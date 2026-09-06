#include "inventory.hpp"

#include <iostream>
#include <string>

namespace {

int usage() {
    std::cerr << "usage: inventory <data-file> <add|deduct|get|list> [sku] [quantity]\n";
    return 2;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) {
        return usage();
    }
    try {
        inventory::Store store(argv[1]);
        const std::string command(argv[2]);
        auto items = store.load();
        if (command == "list") {
            if (argc != 3) return usage();
            std::cout << inventory::render_list(items);
            return 0;
        }
        if (command == "get") {
            if (argc != 4) return usage();
            const std::string sku(argv[3]);
            std::cout << inventory::stock(items, sku) << '\n';
            return 0;
        }
        if (command == "add" || command == "deduct") {
            if (argc != 5) return usage();
            const std::string sku(argv[3]);
            const auto quantity = inventory::parse_quantity(argv[4]);
            if (command == "deduct" && !inventory::deduct(items, sku, quantity)) {
                std::cerr << "insufficient stock\n";
                return 1;
            }
            if (command == "add") inventory::add(items, sku, quantity);
            store.save(items);
            return 0;
        }
        return usage();
    } catch (const inventory::Error& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
