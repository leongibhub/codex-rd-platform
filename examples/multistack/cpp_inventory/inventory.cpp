#include "inventory.hpp"

#include <charconv>
#include <cctype>
#include <fstream>
#include <limits>
#include <sstream>
#include <system_error>

namespace inventory {
namespace {

void validate_sku(const std::string& sku) {
    if (sku.empty()) {
        throw Error("SKU must not be empty");
    }
    for (const unsigned char character : sku) {
        if (std::isspace(character) || character == '\t') {
            throw Error("SKU must not contain whitespace");
        }
    }
}

Items parse_stream(std::istream& input) {
    Items items;
    std::string line;
    std::size_t line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        const auto separator = line.find('\t');
        if (separator == std::string::npos || line.find('\t', separator + 1) != std::string::npos) {
            throw Error("invalid inventory record at line " + std::to_string(line_number));
        }
        const auto sku = line.substr(0, separator);
        validate_sku(sku);
        const auto quantity = parse_quantity(line.substr(separator + 1));
        if (!items.emplace(sku, quantity).second) {
            throw Error("duplicate SKU at line " + std::to_string(line_number));
        }
    }
    if (!input.eof()) {
        throw Error("failed while reading inventory file");
    }
    return items;
}

}  // namespace

Store::Store(std::filesystem::path path) : path_(std::move(path)) {}

Items Store::load() const {
    std::error_code error;
    if (!std::filesystem::exists(path_, error)) {
        if (error) {
            throw Error("cannot inspect inventory file");
        }
        return {};
    }
    std::ifstream input(path_, std::ios::binary);
    if (!input) {
        throw Error("cannot open inventory file");
    }
    return parse_stream(input);
}

void Store::save(const Items& items) const {
    const auto temporary = path_.string() + ".tmp";
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) {
            throw Error("cannot create temporary inventory file");
        }
        for (const auto& [sku, quantity] : items) {
            validate_sku(sku);
            output << sku << '\t' << quantity << '\n';
        }
        output.flush();
        if (!output) {
            throw Error("cannot write inventory file");
        }
    }
    std::error_code error;
    std::filesystem::rename(temporary, path_, error);
    if (error) {
        std::filesystem::remove(temporary, error);
        throw Error("cannot replace inventory file");
    }
}

std::uint64_t parse_quantity(const std::string& text) {
    if (text.empty()) {
        throw Error("quantity must be a non-negative integer");
    }
    for (const unsigned char character : text) {
        if (character < '0' || character > '9') {
            throw Error("quantity must be a non-negative integer");
        }
    }
    std::uint64_t quantity = 0;
    const auto [end, status] = std::from_chars(text.data(), text.data() + text.size(), quantity);
    if (status != std::errc{} || end != text.data() + text.size()) {
        throw Error("quantity is out of range");
    }
    return quantity;
}

void add(Items& items, const std::string& sku, std::uint64_t quantity) {
    validate_sku(sku);
    const auto current = items[sku];
    if (quantity > std::numeric_limits<std::uint64_t>::max() - current) {
        throw Error("stock quantity overflow");
    }
    items[sku] = current + quantity;
}

bool deduct(Items& items, const std::string& sku, std::uint64_t quantity) {
    validate_sku(sku);
    const auto found = items.find(sku);
    if (found == items.end() || found->second < quantity) {
        return false;
    }
    found->second -= quantity;
    return true;
}

std::uint64_t stock(const Items& items, const std::string& sku) {
    validate_sku(sku);
    const auto found = items.find(sku);
    if (found == items.end()) {
        throw Error("SKU not found");
    }
    return found->second;
}

std::string render_list(const Items& items) {
    std::ostringstream output;
    for (const auto& [sku, quantity] : items) {
        output << sku << '\t' << quantity << '\n';
    }
    return output.str();
}

}  // namespace inventory
