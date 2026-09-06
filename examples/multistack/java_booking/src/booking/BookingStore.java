package booking;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Strict local-file repository for one user's meeting-room bookings. */
public final class BookingStore {
    private final Path file;

    public BookingStore(Path file) { this.file = file; }

    public Booking add(String room, LocalDateTime start, LocalDateTime end) throws BookingException {
        validateRoom(room);
        validateInterval(start, end);
        List<Booking> existing = load();
        for (Booking booking : existing) {
            if (room.equals(booking.getRoom()) && start.isBefore(booking.getEnd()) && booking.getStart().isBefore(end)) {
                throw new BookingException("booking conflicts with ID " + booking.getId());
            }
        }
        long nextId = nextId(existing);
        Booking booking = new Booking(nextId, room, start, end);
        existing.add(booking);
        write(existing);
        return booking;
    }

    public void cancel(long id) throws BookingException {
        if (id <= 0) throw new BookingException("ID must be positive");
        List<Booking> existing = load();
        boolean removed = false;
        List<Booking> replacement = new ArrayList<Booking>();
        for (Booking booking : existing) {
            if (booking.getId() == id) removed = true; else replacement.add(booking);
        }
        if (!removed) throw new BookingException("booking ID not found");
        write(replacement);
    }

    public List<Booking> list(String room) throws BookingException {
        if (room != null) validateRoom(room);
        List<Booking> results = new ArrayList<Booking>();
        for (Booking booking : load()) if (room == null || room.equals(booking.getRoom())) results.add(booking);
        Collections.sort(results, new Comparator<Booking>() {
            @Override public int compare(Booking left, Booking right) {
                int compared = left.getRoom().compareTo(right.getRoom());
                if (compared != 0) return compared;
                compared = left.getStart().compareTo(right.getStart());
                if (compared != 0) return compared;
                return Long.compare(left.getId(), right.getId());
            }
        });
        return results;
    }

    private List<Booking> load() throws BookingException {
        if (!Files.exists(file)) return new ArrayList<Booking>();
        List<String> lines;
        try { lines = Files.readAllLines(file, StandardCharsets.UTF_8); }
        catch (IOException exception) { throw new BookingException("cannot read data file", exception); }
        List<Booking> results = new ArrayList<Booking>();
        Set<Long> ids = new HashSet<Long>();
        for (String line : lines) {
            String[] fields = line.split("\\|", -1);
            if (fields.length != 4) throw new BookingException("malformed persisted record");
            long id;
            LocalDateTime start;
            LocalDateTime end;
            try {
                id = Long.parseLong(fields[0]);
                start = LocalDateTime.parse(fields[2]);
                end = LocalDateTime.parse(fields[3]);
            } catch (NumberFormatException | DateTimeParseException exception) {
                throw new BookingException("malformed persisted record", exception);
            }
            if (id <= 0 || !ids.add(id)) throw new BookingException("malformed persisted record");
            validateRoom(fields[1]);
            validateInterval(start, end);
            for (Booking existing : results) {
                if (fields[1].equals(existing.getRoom()) && start.isBefore(existing.getEnd()) && existing.getStart().isBefore(end)) {
                    throw new BookingException("malformed persisted record");
                }
            }
            results.add(new Booking(id, fields[1], start, end));
        }
        return results;
    }

    private void write(List<Booking> bookings) throws BookingException {
        Path absolute = file.toAbsolutePath();
        Path parent = absolute.getParent();
        Path temporary = null;
        try {
            if (parent != null) Files.createDirectories(parent);
            temporary = Files.createTempFile(parent, absolute.getFileName().toString(), ".tmp");
            List<String> lines = new ArrayList<String>();
            for (Booking booking : bookings) {
                lines.add(booking.getId() + "|" + booking.getRoom() + "|" + booking.getStart() + "|" + booking.getEnd());
            }
            Files.write(temporary, lines, StandardCharsets.UTF_8);
            try {
                Files.move(temporary, absolute, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            } catch (AtomicMoveNotSupportedException unsupported) {
                Files.move(temporary, absolute, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (IOException exception) {
            throw new BookingException("cannot write data file", exception);
        } finally {
            if (temporary != null) try { Files.deleteIfExists(temporary); } catch (IOException ignored) { }
        }
    }

    private static long nextId(List<Booking> bookings) throws BookingException {
        long maximum = 0;
        for (Booking booking : bookings) maximum = Math.max(maximum, booking.getId());
        if (maximum == Long.MAX_VALUE) throw new BookingException("no ID remains");
        return maximum + 1;
    }

    static void validateRoom(String room) throws BookingException {
        if (room == null || room.isEmpty() || room.indexOf('|') >= 0 || room.indexOf('\n') >= 0 || room.indexOf('\r') >= 0) {
            throw new BookingException("room must be non-empty and contain no record separators");
        }
    }

    static void validateInterval(LocalDateTime start, LocalDateTime end) throws BookingException {
        if (start == null || end == null || !start.isBefore(end)) throw new BookingException("start must precede end");
    }
}
