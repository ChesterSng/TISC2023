first_return_value = 211278
second_return_value = 544885

def generate_next_value(prev_value):
    prev_value = int(prev_value)
    current = prev_value ^ 844742906  # XOR operation

    # Convert to binary and ensure a 32-bit length
    current = bin(current)[2:].zfill(32)

    # Bit manipulation (reordering)
    first = current[:7]
    second = current[7:]
    current = second + first

    # Convert back to decimal
    current = int(current, 2)

    return current % 1000000, current

for first in range(first_return_value, 2**32, 1000000):
    if generate_next_value(first)[0] == second_return_value:
        print(generate_next_value(generate_next_value(first)[1])[0])

