package booking;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.List;

/** Developer unit tests for REQ-MATRIX-JAVA. */
public final class BookingStoreTest {
    private static int assertions;

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("usage: BookingStoreTest <test-directory>");
        }
        Path directory = Paths.get(args[0]);
        Files.createDirectories(directory);
        testAddConflictAndAdjacency(directory.resolve("conflict.bookings"));
        testCancelAndOrderedListing(directory.resolve("listing.bookings"));
        testInvalidInputDoesNotWrite(directory.resolve("invalid.bookings"));
        testMalformedPersistenceIsRejected(directory.resolve("malformed.bookings"));
        System.out.println("BookingStoreTest: " + assertions + " assertions passed");
    }

    private static void testAddConflictAndAdjacency(Path data) throws Exception {
        fresh(data);
        BookingStore store = new BookingStore(data);
        Booking first = store.add("Orchid", time("2026-09-06T09:00"), time("2026-09-06T10:00"));
        expect(first.getId() == 1L, "first ID");
        byte[] committed = Files.readAllBytes(data);
        expectThrows(BookingException.class, () -> store.add("Orchid", time("2026-09-06T09:30"), time("2026-09-06T10:30")), "overlap rejected");
        expect(equalBytes(committed, Files.readAllBytes(data)), "conflict does not write");
        Booking adjacent = store.add("Orchid", time("2026-09-06T10:00"), time("2026-09-06T11:00"));
        expect(adjacent.getId() == 2L, "adjacent allowed");
        Booking otherRoom = store.add("Lily", time("2026-09-06T09:30"), time("2026-09-06T10:30"));
        expect(otherRoom.getId() == 3L, "different room allowed");
    }

    private static void testCancelAndOrderedListing(Path data) throws Exception {
        fresh(data);
        BookingStore store = new BookingStore(data);
        Booking late = store.add("Zeta", time("2026-09-06T13:00"), time("2026-09-06T14:00"));
        Booking early = store.add("Alpha", time("2026-09-06T09:00"), time("2026-09-06T10:00"));
        List<Booking> all = store.list(null);
        expect(all.get(0).equals(early), "list sorts by room then start");
        expect(all.get(1).equals(late), "list retains second record");
        expect(store.list("Alpha").size() == 1, "room filter");
        store.cancel(late.getId());
        expect(store.list(null).size() == 1, "cancel removes target only");
        byte[] committed = Files.readAllBytes(data);
        expectThrows(BookingException.class, () -> store.cancel(999L), "unknown cancel rejected");
        expect(equalBytes(committed, Files.readAllBytes(data)), "unknown cancel does not write");
    }

    private static void testInvalidInputDoesNotWrite(Path data) throws Exception {
        fresh(data);
        BookingStore store = new BookingStore(data);
        store.add("Maple", time("2026-09-06T09:00"), time("2026-09-06T10:00"));
        byte[] committed = Files.readAllBytes(data);
        expectThrows(BookingException.class, () -> store.add("", time("2026-09-06T10:00"), time("2026-09-06T11:00")), "empty room");
        expectThrows(BookingException.class, () -> store.add("Bad\nRoom", time("2026-09-06T10:00"), time("2026-09-06T11:00")), "separator room");
        expectThrows(BookingException.class, () -> store.add("Maple", time("2026-09-06T10:00"), time("2026-09-06T10:00")), "empty interval");
        expect(equalBytes(committed, Files.readAllBytes(data)), "validation errors do not write");
    }

    private static void testMalformedPersistenceIsRejected(Path data) throws Exception {
        fresh(data);
        Files.write(data, "not-a-record\n".getBytes(StandardCharsets.UTF_8));
        BookingStore store = new BookingStore(data);
        expectThrows(BookingException.class, () -> store.list(null), "malformed data rejected");
        expect(equalBytes("not-a-record\n".getBytes(StandardCharsets.UTF_8), Files.readAllBytes(data)), "bad data is not repaired by read");
        Files.write(data, ("1|Orchid|2026-09-06T09:00|2026-09-06T10:00\n"
                + "2|Orchid|2026-09-06T09:30|2026-09-06T10:30\n").getBytes(StandardCharsets.UTF_8));
        expectThrows(BookingException.class, () -> store.list(null), "persisted conflict rejected");
    }

    private static LocalDateTime time(String value) {
        return LocalDateTime.parse(value);
    }

    private static void fresh(Path data) throws IOException {
        Files.deleteIfExists(data);
    }

    private static boolean equalBytes(byte[] left, byte[] right) {
        if (left.length != right.length) return false;
        for (int i = 0; i < left.length; i++) if (left[i] != right[i]) return false;
        return true;
    }

    private static void expect(boolean condition, String label) {
        assertions++;
        if (!condition) throw new AssertionError(label);
    }

    private static void expectThrows(Class<? extends Exception> type, ThrowingOperation operation, String label) throws Exception {
        assertions++;
        try {
            operation.run();
        } catch (Exception exception) {
            if (type.isInstance(exception)) return;
            throw new AssertionError(label + ": unexpected " + exception, exception);
        }
        throw new AssertionError(label + ": exception not thrown");
    }

    @FunctionalInterface
    private interface ThrowingOperation { void run() throws Exception; }
}
