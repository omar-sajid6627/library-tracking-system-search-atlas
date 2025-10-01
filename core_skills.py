import random

rand_list = [random.randint(1,20) for _ in range(10)]

list_comprehension_below_10 = [num for num in rand_list if num < 10]

filter_below_10 = list(filter(lambda x: x < 10, rand_list))

print("Random list:", rand_list)
print("Numbers below 10 with list comprehension:", list_comprehension_below_10)
print("Numbers below 10 with filter:", filter_below_10)