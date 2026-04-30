#!/usr/bin/env python3

# A simple hello world script with user input

def main():
    name = input("Enter your name: ").strip()
    print(
        "***************************************",
        f"* Hello, World! *",
        f"* Hello, {name.capitalize()}! *",
        "* Welcome to the program! *",
        "***************************************"
    )

if __name__ == "__main__":
    main()