## Simple Walkthrough with 0 APRs

```json
{
	"budget": 30,
	"cards": [{
		"cardNickName": "Card1",
		"cardApr": 0,
		"cardBalance": 51,
		"minPayment": 10,
		"maxPayment": 51,
		"actualPayments": 10
	},
	{
		"cardNickName": "Card2",
		"cardApr": 0,
		"cardBalance": 100,
		"minPayment": 10,
		"maxPayment": 100,
		"actualPayments": 10
	},
	{
		"cardNickName": "Card3",
		"cardApr": 0,
		"cardBalance": 51,
		"minPayment": 10,
		"maxPayment": 51,
		"actualPayments": 10
	}
	]
}
```

It's easy to see that there will never be any accrued interest and as such, any payment plan that fully uses 
the budget should be optimal.

* Allocation API

| balance 1 | balance 2 | balance 3 | Month |
|-----------|-----------|-----------|-------|
|    51     |    100    |     51    |   1   |

The data always begins with the current balance. The question is then: 

```
How should I split my $30.00 budget on these 3 cards so that the total balance with accrued interest 
(this time next month) is lower than what it would be if I only made the minimum payments?
```

Well for the minimum payment of $10 the next balance should be `(balance - 10) * (1 + 0 / 12)` since the APR is 0 for each card.
Unsurprisingly the optimal suggested payment allocation is also $10.00 for each card!

Send a post request to the the [API](https://ccrdapi.herokuapp.com/cards) with the `json` content above. The result should be
```json
{
    "budget": 30,
    "solution": "Optimal",
    "initialBalance": 202,
    "endBalanceOnMinimumPayment": 172,
    "endBalanceOnCurrentPayment": 172,
    "endBalanceOnSuggestedPayment": 172,
    "updatedCards": [
        {
            "cardNickName": "Card1",
            "cardBalance": 51,
            "cardApr": 0,
            "minPayment": 10,
            "maxPayment": 51,
            "actualPayments": 10,
            "suggestedPayment": 10,
            "nextBalanceOnSuggested": 41,
            "nextBalanceOnMin": 41,
            "nextBalanceOnCurrentPayment": 41
        },
        {
            "cardNickName": "Card2",
            "cardBalance": 100,
            "cardApr": 0,
            "minPayment": 10,
            "maxPayment": 100,
            "actualPayments": 10,
            "suggestedPayment": 10,
            "nextBalanceOnSuggested": 90,
            "nextBalanceOnMin": 90,
            "nextBalanceOnCurrentPayment": 90
        },
        {
            "cardNickName": "Card3",
            "cardBalance": 51,
            "cardApr": 0,
            "minPayment": 10,
            "maxPayment": 51,
            "actualPayments": 10,
            "suggestedPayment": 10,
            "nextBalanceOnSuggested": 41,
            "nextBalanceOnMin": 41,
            "nextBalanceOnCurrentPayment": 41
        }
    ]
}
```

But what's more interesting is to look at the next 12 months of this process.

* Progress API

Use this [API](https://ccrdapi.herokuapp.com/cards/12) and inspect the output.

Assume you are making minimum payments (or suggested payments for that matter)

| balance 1 | balance 2 | balance 3 | Month |
|-----------|-----------|-----------|-------|
|    51     |    100    |     51    |   1   |
|    41     |     90    |     41    |   2   |
|    31     |     80    |     31    |   3   |
|    21     |     70    |     21    |   4   |
|    11     |     60    |     11    |   5   |
|     1     |     50    |      1    |   6   |

Well at this point, payments of $1 are required for Card1 and Card3 but that means that there is $18 left
with a budget of $30.00 that should be allocated. 

Well at this point there is a *minimum payment* reallocation which simply adds more money to the payment for the Card with
1) Remaining balance more than payment
2) Highest APR

In this case Card2's payment goes from $10.00 to $18.00 + $10.00 = $28.00

| balance 1 | balance 2 | balance 3 | Month |
|-----------|-----------|-----------|-------|
|    51     |    100    |     51    |   1   |
|    41     |     90    |     41    |   2   |
|    31     |     80    |     31    |   3   |
|    21     |     70    |     21    |   4   |
|    11     |     60    |     11    |   5   |
|     1     |     50    |      1    |   6   |
|     0     |     22    |      0    |   7   |
|     0     |     0     |      0    |   8   |

For the optimal payments, the reallocation isn't done manually, we simply compute the balances one a time
and the linear programming functions take care of the calculation since the total balances are updated after
each iteration.

**Note that we barely spoke of maximum payments at all** They are used as a constraint on the linear programming problem.
So if a user provides a maximum payment that is less than the budget or the balance of a card, the suggested payment for that
card will not go over the maximum payment even if there is room in the budget!

## Minimum Payment Adjustment
The minimum payment will not remain the same if the balance decreases. This is one of the assumptions of this API.
There is a constant rate calculated as `minimum payment / balance` that is applied to each balance to adjust the minimum
payment since this is a constraint for the linear programming problem. 

Say at month 6 the minimum payments have not changed for Card1. Then the constraints applied to the optimal solution would imply that
despite a balance of only $1.00, a payment of at least $10.00 should be made. That makes no sense! So initially a flat rate
of `10 / 51 ~ .2` is used to adjust the minimum payment at month 6. So `.2 * 1 = .2` which then ease the constraints for the Card.

P.S: Many simple assumptions were made for the simplicity of this project. These APIs are best used for cards/loans with
fixed APR (note APY is not being used) and no additional expenses etc.

For a user friendly experience, please checkout this [tool](https://pymtallocation.herokuapp.com/). It is still under construction 
