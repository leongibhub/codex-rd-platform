package booking;

import java.time.LocalDateTime;

/** Immutable committed reservation. */
public final class Booking {
    private final long id;
    private final String room;
    private final LocalDateTime start;
    private final LocalDateTime end;

    public Booking(long id, String room, LocalDateTime start, LocalDateTime end) {
        this.id = id;
        this.room = room;
        this.start = start;
        this.end = end;
    }

    public long getId() { return id; }
    public String getRoom() { return room; }
    public LocalDateTime getStart() { return start; }
    public LocalDateTime getEnd() { return end; }

    @Override public boolean equals(Object other) {
        if (!(other instanceof Booking)) return false;
        Booking value = (Booking) other;
        return id == value.id && room.equals(value.room) && start.equals(value.start) && end.equals(value.end);
    }

    @Override public int hashCode() {
        return (int) (id ^ (id >>> 32)) * 31 + room.hashCode() * 17 + start.hashCode() * 7 + end.hashCode();
    }
}
