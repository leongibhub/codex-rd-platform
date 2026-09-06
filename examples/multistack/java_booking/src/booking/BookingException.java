package booking;

/** Expected validation, conflict, and persistence-format failure. */
public final class BookingException extends Exception {
    public BookingException(String message) { super(message); }
    public BookingException(String message, Throwable cause) { super(message, cause); }
}
