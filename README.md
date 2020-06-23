# Optimizing Payment Plan - Using linear Programming in Python coupled with FastAPI to suggest credit card payment

Given two (or more) credit cards, assume after all transactions have posted and balances are final, if I had 
budget of `$X`, how much should I put towards credit card 1 and how much should I put towards credit card 2?

There are two API routes in this project and the outputs of each will be better explained.

### Cards and Configuration
```json
{
    "budget": 100,
    "cards": [
        {
            "cardNickName": "Prime",
            "cardBalance": 1000,
            "cardApr": 15,
            "minPayment": 20,
            "maxPayment": null,
            "actualPayments": 50
        },
        {
            "cardNickName": "United",
            "cardBalance": 1800,
            "cardApr": 18,
            "minPayment": 36,
            "maxPayment": null,
            "actualPayments": 50
        }
    ]
}
```

If I have a budget of 100, how should I split it towards each card? Well if I split it in the middle then what
should I expect my balance to be next month.

**Right here you should notice that there is an assumption that no additional charges are added to the credit 
card from when payment is made to when interest accrued is applied.** This is obiously not realistic but I often
stop using some credit cards once they've reached a certain balance. For that reason, these APIs are actually 
useful.

Alright back to the payment allocations. What happens if I pay $50 on each card now. The balances should be
$950.00 and $1750.00 respectively for Prime and United. All we need to do now is apply the APR on these balances.

For example `$[(1000 - 50) * (1 + .15/12)] = $961.875` is what I expect my Prime balance to be next month
when I am ready to make a payment. That's great and all but my goal is to allocate the payments so that my total
balance of $2800.00 is at the lowest possible next month based on the payment and budget constraints. For this,
I turned to [linear programming](https://github.com/coin-or/pulp). The output of the first API is as follows:

```json
{
    "budget": 100,
    "solution": "Optimal",
    "initialBalance": 2800,
    "endBalanceOnMinimumPayment": 2782.71,
    "endBalanceOnCurrentPayment": 2738.125,
    "endBalanceOnSuggestedPayment": 2738.0499999999997,
    "updatedCards": [
        {
            "cardNickName": "Prime",
            "cardBalance": 1000,
            "cardApr": 15,
            "minPayment": 20,
            "suggestedPayment": 20,
            "nextBalanceOnSuggested": 992.25,
            "nextBalanceOnMin": 992.25,
            "nextBalanceOnCurrentPayment": 961.875,
            "maxPayment": null,
            "actualPayments": 50
        },
        {
            "cardNickName": "United",
            "cardBalance": 1800,
            "cardApr": 18,
            "minPayment": 36,
            "suggestedPayment": 80,
            "nextBalanceOnSuggested": 1745.7999999999997,
            "nextBalanceOnMin": 1790.4599999999998,
            "nextBalanceOnCurrentPayment": 1776.2499999999998,
            "maxPayment": null,
            "actualPayments": 50
        }
    ]
}
```

It turns out that the *suggestedPayment* for the Prime card is $20 and $80 for the United card. Obviously this
is not optimal for the Prime card balance but it is optimal for the total balance i.e. both cards. This is alright
but I am only saving cents by choosing the suggested solution. Obviosuly with more cards added to the mix there
may just be real $$ in the tens saved!

I am also interested in seeing how the optimal approach at the end of each month works. Again problem lies in 
the rather simple assumptions. But there is a second API that provides a comparison of:

1) Paying the minimum balance each month
2) Paying the same amount each month
3) Using the linear programming solutions each month

A couple of things to keep in mind. 

1) The minimum payment is not kept constant. I assume a constant rate `minimum balance / balance`
that is multiplied to the remaining balance each month.
2) When the current payments reach a point where one credit card is paid off (or nearly paid off), the payments
on that card are reallocated first to the card with the highest APR, then to the second and so on.

This is the output of this API
FYI - this is written July 2019 and so we have the projection through July 2020
```json
{
    "progress": [
        {
            "cardNickName": "Prime",
            "projection": [
                {
                    "July": {
                        "nextBalanceOnMin": 1000,
                        "nextBalanceOnCurrentPayment": 1000,
                        "nextBalanceOnSuggested": 1000
                    }
                },
                {
                    "August": {
                        "nextBalanceOnMin": 992.25,
                        "nextBalanceOnCurrentPayment": 961.88,
                        "nextBalanceOnSuggested": 992.25
                    }
                },
                {
                    "September": {
                        "nextBalanceOnMin": 984.56,
                        "nextBalanceOnCurrentPayment": 923.28,
                        "nextBalanceOnSuggested": 984.4031
                    }
                },
                {
                    "October": {
                        "nextBalanceOnMin": 976.93,
                        "nextBalanceOnCurrentPayment": 884.2,
                        "nextBalanceOnSuggested": 976.4581
                    }
                },
                {
                    "November": {
                        "nextBalanceOnMin": 969.36,
                        "nextBalanceOnCurrentPayment": 844.63,
                        "nextBalanceOnSuggested": 968.4138
                    }
                },
                {
                    "December": {
                        "nextBalanceOnMin": 961.85,
                        "nextBalanceOnCurrentPayment": 804.56,
                        "nextBalanceOnSuggested": 960.269
                    }
                },
                {
                    "January": {
                        "nextBalanceOnMin": 954.4,
                        "nextBalanceOnCurrentPayment": 763.99,
                        "nextBalanceOnSuggested": 952.0224
                    }
                },
                {
                    "February": {
                        "nextBalanceOnMin": 947,
                        "nextBalanceOnCurrentPayment": 722.91,
                        "nextBalanceOnSuggested": 943.6727
                    }
                },
                {
                    "March": {
                        "nextBalanceOnMin": 939.66,
                        "nextBalanceOnCurrentPayment": 681.32,
                        "nextBalanceOnSuggested": 935.2186
                    }
                },
                {
                    "April": {
                        "nextBalanceOnMin": 932.38,
                        "nextBalanceOnCurrentPayment": 639.21,
                        "nextBalanceOnSuggested": 926.6588
                    }
                },
                {
                    "May": {
                        "nextBalanceOnMin": 925.15,
                        "nextBalanceOnCurrentPayment": 596.58,
                        "nextBalanceOnSuggested": 917.992
                    }
                },
                {
                    "June": {
                        "nextBalanceOnMin": 917.98,
                        "nextBalanceOnCurrentPayment": 553.41,
                        "nextBalanceOnSuggested": 909.2169
                    }
                },
                {
                    "July": {
                        "nextBalanceOnMin": 910.87,
                        "nextBalanceOnCurrentPayment": 509.7,
                        "nextBalanceOnSuggested": 900.3321
                    }
                }
            ]
        },
        {
            "cardNickName": "United",
            "projection": [
                {
                    "July": {
                        "nextBalanceOnMin": 1800,
                        "nextBalanceOnCurrentPayment": 1800,
                        "nextBalanceOnSuggested": 1800
                    }
                },
                {
                    "August": {
                        "nextBalanceOnMin": 1790.46,
                        "nextBalanceOnCurrentPayment": 1776.25,
                        "nextBalanceOnSuggested": 1745.8
                    }
                },
                {
                    "September": {
                        "nextBalanceOnMin": 1780.97,
                        "nextBalanceOnCurrentPayment": 1752.14,
                        "nextBalanceOnSuggested": 1690.787
                    }
                },
                {
                    "October": {
                        "nextBalanceOnMin": 1771.53,
                        "nextBalanceOnCurrentPayment": 1727.67,
                        "nextBalanceOnSuggested": 1634.9488
                    }
                },
                {
                    "November": {
                        "nextBalanceOnMin": 1762.14,
                        "nextBalanceOnCurrentPayment": 1702.84,
                        "nextBalanceOnSuggested": 1578.273
                    }
                },
                {
                    "December": {
                        "nextBalanceOnMin": 1752.8,
                        "nextBalanceOnCurrentPayment": 1677.63,
                        "nextBalanceOnSuggested": 1520.7471
                    }
                },
                {
                    "January": {
                        "nextBalanceOnMin": 1743.51,
                        "nextBalanceOnCurrentPayment": 1652.04,
                        "nextBalanceOnSuggested": 1462.3583
                    }
                },
                {
                    "February": {
                        "nextBalanceOnMin": 1734.27,
                        "nextBalanceOnCurrentPayment": 1626.07,
                        "nextBalanceOnSuggested": 1403.0937
                    }
                },
                {
                    "March": {
                        "nextBalanceOnMin": 1725.08,
                        "nextBalanceOnCurrentPayment": 1599.71,
                        "nextBalanceOnSuggested": 1342.9401
                    }
                },
                {
                    "April": {
                        "nextBalanceOnMin": 1715.94,
                        "nextBalanceOnCurrentPayment": 1572.96,
                        "nextBalanceOnSuggested": 1281.8842
                    }
                },
                {
                    "May": {
                        "nextBalanceOnMin": 1706.85,
                        "nextBalanceOnCurrentPayment": 1545.8,
                        "nextBalanceOnSuggested": 1219.9125
                    }
                },
                {
                    "June": {
                        "nextBalanceOnMin": 1697.8,
                        "nextBalanceOnCurrentPayment": 1518.24,
                        "nextBalanceOnSuggested": 1157.0112
                    }
                },
                {
                    "July": {
                        "nextBalanceOnMin": 1688.8,
                        "nextBalanceOnCurrentPayment": 1490.26,
                        "nextBalanceOnSuggested": 1093.1664
                    }
                }
            ]
        }
    ]
}
```

Note that by July 2019 the total remaining balance if the linear programming approach is taken is only $4 less
than when the the current payment allocation works.

[API Docs](https://ccrdapi.herokuapp.com/docs)
