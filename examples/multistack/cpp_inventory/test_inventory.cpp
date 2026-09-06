#include "inventory.hpp"

#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_throws(const std::function<void()>& operation, const std::string& message) {
    try {
        operation();
    } catch (const inventory::Error&) {
        return;
    }
    throw std::runtime_error(message);
}

std::filesystem::path test_file(const std::filesystem::path& directory, const std::string& name) {
    std::filesystem::create_directories(directory);
    const auto path = directory / name;
    std::error_code error;
    std::filesystem::remove(path, error);
    if (error) {
        throw std::runtime_error("unable to reset controlled test fixture");
    }
    return path;
}

std::string read_bytes(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

void test_add_and_reload(const std::filesystem::path& directory) {
    const auto path = test_file(directory, "add-and-reload.tsv");
    inventory::Store store(path);
    auto items = store.load();
    inventory::add(items, "apple", 3);
    inventory::add(items, "apple", 2);
    store.save(items);

    const auto reloaded = inventory::Store(path).load();
    require(reloaded.at("apple") == 5, "TC-CPP-001: additions must accumulate and persist");
}

void test_insufficient_deduction_does_not_write(const std::filesystem::path& directory) {
    const auto path = test_file(directory, "insufficient.tsv");
    inventory::Store store(path);
    auto items = store.load();
    inventory::add(items, "banana", 2);
    store.save(items);
    const auto before = read_bytes(path);

    require(!inventory::deduct(items, "banana", 3), "TC-CPP-002: insufficient deduction must fail");
    require(read_bytes(path) == before, "TC-CPP-002: failed deduction must not write the file");
    require(inventory::Store(path).load().at("banana") == 2, "TC-CPP-002: failed deduction must not change stock");
}

void test_listing_is_sku_ordered(const std::filesystem::path& directory) {
    const auto path = test_file(directory, "ordered.tsv");
    inventory::Store store(path);
    auto items = store.load();
    inventory::add(items, "zebra", 1);
    inventory::add(items, "apple", 2);
    inventory::add(items, "mango", 3);
    store.save(items);

    const auto listed = inventory::Store(path).load();
    const auto rendered = inventory::render_list(listed);
    require(rendered == "apple\t2\nmango\t3\nzebra\t1\n", "TC-CPP-003: list must have deterministic SKU order");
}

void test_bad_persistence_is_rejected(const std::filesystem::path& directory) {
    const auto path = test_file(directory, "bad-data.tsv");
    {
        std::ofstream output(path, std::ios::binary);
        output << "valid\t2\ninvalid\t-1\n";
    }
    require_throws([&] { static_cast<void>(inventory::Store(path).load()); },
                   "TC-CPP-005: malformed data must be rejected");
}

void test_invalid_skus_and_quantities_are_rejected(const std::filesystem::path& directory) {
    const auto path = test_file(directory, "validation.tsv");
    inventory::Store store(path);
    auto items = store.load();
    require_throws([&] { inventory::add(items, "", 1); }, "TC-CPP-006: empty SKU must fail");
    require_throws([&] { inventory::add(items, "two words", 1); }, "TC-CPP-006: whitespace SKU must fail");
    require_throws([&] { static_cast<void>(inventory::stock(items, "two words")); }, "TC-CPP-006: get SKU must be validated");
    require_throws([&] { static_cast<void>(inventory::parse_quantity("-1")); }, "TC-CPP-006: negative quantity must fail");
    require_throws([&] { static_cast<void>(inventory::parse_quantity("1.0")); }, "TC-CPP-006: decimal quantity must fail");
    require_throws([&] { static_cast<void>(inventory::parse_quantity("18446744073709551616")); }, "TC-CPP-006: overflow quantity must fail");
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: test_inventory <build-test-directory>\n";
        return 2;
    }

    try {
        const std::filesystem::path directory(argv[1]);
        test_add_and_reload(directory);
        test_insufficient_deduction_does_not_write(directory);
        test_listing_is_sku_ordered(directory);
        test_bad_persistence_is_rejected(directory);
        test_invalid_skus_and_quantities_are_rejected(directory);
        std::cout << "5 tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
