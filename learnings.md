

```json
{
    "order":{{$}}
}
```

- {{$}} in postman will show you list of all variables in the current scope


- query params are case sensitive, so `type=Fiction` will not match `type=fiction` in the code above.
- and `limit=10` and `Limit=10` are different too.