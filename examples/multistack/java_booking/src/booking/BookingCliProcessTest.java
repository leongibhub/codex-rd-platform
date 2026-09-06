package booking;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

/** Separate-process CLI checks for TC-JAVA-006 and TC-JAVA-007. */
public final class BookingCliProcessTest {
    private static int assertions;

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("usage: BookingCliProcessTest <test-directory>");
        Path directory = Paths.get(args[0]);
        Files.createDirectories(directory);
        Path data = directory.resolve("cli.bookings");
        Files.deleteIfExists(data);
        testJavaExecutableName();

        Result first = invoke(data, "add", "Orchid", "2026-09-06T09:00", "2026-09-06T10:00");
        expect(first.exitCode == 0 && "1".equals(first.stdout.trim()), "add succeeds in child process");
        byte[] committed = Files.readAllBytes(data);
        expect(invoke(data, "add", "Orchid", "2026-09-06T09:30", "2026-09-06T10:30").exitCode != 0, "overlap fails in child process");
        expect(equalBytes(committed, Files.readAllBytes(data)), "conflict child process does not write");
        expect(invoke(data, "add", "Orchid", "2026-09-06T10:00", "2026-09-06T11:00").exitCode == 0, "adjacent succeeds in child process");
        Result listed = invoke(data, "list");
        expect(listed.exitCode == 0 && listed.stdout.contains("1|Orchid|2026-09-06T09:00|2026-09-06T10:00"), "new process reloads first booking");
        expect(listed.stdout.contains("2|Orchid|2026-09-06T10:00|2026-09-06T11:00"), "new process reloads adjacent booking");
        expect(invoke(data, "cancel", "1").exitCode == 0, "cancel succeeds in fresh process");
        expect(!invoke(data, "list").stdout.contains("1|Orchid"), "cancel is durable in fresh process");
        byte[] afterCancel = Files.readAllBytes(data);
        expect(invoke(data, "add", "Orchid", "bad-time", "2026-09-06T12:00").exitCode != 0, "invalid timestamp fails");
        expect(equalBytes(afterCancel, Files.readAllBytes(data)), "invalid CLI input does not write");
        expect(invoke(data, "list", "Orchid", "extra").exitCode != 0, "extra argument fails");
        System.out.println("BookingCliProcessTest: " + assertions + " assertions passed");
    }

    private static void testJavaExecutableName() {
        expect("java.exe".equals(javaExecutableName("Windows 11")), "Windows launcher has .exe suffix");
        expect("java".equals(javaExecutableName("Linux")), "Linux launcher has no suffix");
        expect("java".equals(javaExecutableName("Mac OS X")), "macOS launcher has no suffix");
    }

    private static Result invoke(Path data, String... command) throws IOException, InterruptedException {
        List<String> args = new ArrayList<String>();
        args.add(Paths.get(System.getProperty("java.home"), "bin", javaExecutableName(System.getProperty("os.name"))).toString());
        args.add("-cp");
        args.add(System.getProperty("java.class.path"));
        args.add("booking.BookingCli");
        args.add(data.toString());
        args.addAll(Arrays.asList(command));
        Process process = new ProcessBuilder(args).redirectErrorStream(true).start();
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int count;
        while ((count = process.getInputStream().read(buffer)) >= 0) output.write(buffer, 0, count);
        return new Result(process.waitFor(), new String(output.toByteArray(), StandardCharsets.UTF_8));
    }

    static String javaExecutableName(String osName) {
        return osName != null && osName.toLowerCase(Locale.ROOT).startsWith("windows") ? "java.exe" : "java";
    }

    private static boolean equalBytes(byte[] left, byte[] right) {
        return Arrays.equals(left, right);
    }

    private static void expect(boolean condition, String label) {
        assertions++;
        if (!condition) throw new AssertionError(label);
    }

    private static final class Result {
        private final int exitCode;
        private final String stdout;
        private Result(int exitCode, String stdout) { this.exitCode = exitCode; this.stdout = stdout; }
    }
}
