#pragma once

#include <cstdint>
#include <filesystem>
#include <map>
#include <stdexcept>
#include <string>

namespace inventory {

class Error : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

using Items = std::map<std::string, std::uint64_t>;

class Store {
public:
    explicit Store(std::filesystem::path path);
    Items load() const;
    void save(const Items& items) const;

private:
    std::filesystem::path path_;
};

std::uint64_t parse_quantity(const std::string& text);
void add(Items& items, const std::string& sku, std::uint64_t quantity);
bool deduct(Items& items, const std::string& sku, std::uint64_t quantity);
std::uint64_t stock(const Items& items, const std::string& sku);
std::string render_list(const Items& items);

}  // namespace inventory
