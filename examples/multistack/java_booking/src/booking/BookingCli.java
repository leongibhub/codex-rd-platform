package booking;

import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;

/** CLI entry point. Expected errors are displayed without a stack trace. */
public final class BookingCli {
    private BookingCli() { }

    public static void main(String[] args) {
        try {
            run(args);
        } catch (BookingException | DateTimeParseException exception) {
            System.err.println("error: " + exception.getMessage());
            System.exit(2);
        }
    }

    static void run(String[] args) throws BookingException {
        if (args.length < 2) throw new BookingException("usage: booking <data-file> <add|cancel|list> ...");
        BookingStore store = new BookingStore(Paths.get(args[0]));
        String command = args[1];
        if ("add".equals(command)) {
            if (args.length != 5) throw new BookingException("usage: booking <data-file> add <room> <start> <end>");
            Booking booking = store.add(args[2], LocalDateTime.parse(args[3]), LocalDateTime.parse(args[4]));
            System.out.println(booking.getId());
        } else if ("cancel".equals(command)) {
            if (args.length != 3) throw new BookingException("usage: booking <data-file> cancel <id>");
            try { store.cancel(Long.parseLong(args[2])); }
            catch (NumberFormatException exception) { throw new BookingException("ID must be a positive decimal integer", exception); }
        } else if ("list".equals(command)) {
            if (args.length != 2 && args.length != 3) throw new BookingException("usage: booking <data-file> list [room]");
            List<Booking> bookings = store.list(args.length == 3 ? args[2] : null);
            for (Booking booking : bookings) System.out.println(booking.getId() + "|" + booking.getRoom() + "|" + booking.getStart() + "|" + booking.getEnd());
        } else {
            throw new BookingException("unknown command");
        }
    }
}
