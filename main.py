import pulp
import json
import string
import typing
import datetime
import functools
import itertools
from fastapi import FastAPI
from pydantic import BaseModel, validator
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http:localhost",
    "http:localhost:8080",
    "http://0.0.0.0:1234"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_objective = """
Find out if you could save on your total credit/loan balance by changing how much you put on each card. \
We wish to suggest how much you should put towards each of your credit cards so that your next month total balance \
is the lowest possible.

We will use the percentage of your minimum payment per your balance to adjust minimum balance
Or we use a 3% rate is used 
"""

months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
]


class Card(BaseModel, object):
    cardNickName: str
    cardBalance: float
    cardApr: float
    minPayment: float
    maxPayment: float = None
    actualPayments: float = None
    min2balancerate: float = 0.0
    minProjections: typing.List[float] = [0.0] * 13
    actualProjections: typing.List[float] = [0.0] * 13

    def update_min(self):
        """
        With the validators this is obsolete!
        :return:
        """
        if self.minPayment > self.cardBalance:
            self.minPayment = self.cardBalance

    # balance must always be positive
    @validator('cardBalance')
    def positive_balance(cls, v):
        if v <= 0:
            raise ValueError('Balance Must Be Positive')
        return v

    # apr must always be positive
    @validator('cardApr')
    def positive_apr(cls, v):
        if v <= 0:
            raise ValueError('APR Must Be Positive')
        return v

    # minimum payment must be positive
    @validator('minPayment')
    def positive_min(cls, v):
        if v <= 0:
            raise ValueError('Minimum Payment Must Be Positive')
        return v

    # maximum payment must be positive
    @validator('maxPayment')
    def positive_max(cls, v):
        if v <= 0:
            raise ValueError('Maximum Payment Must Be Positive')
        return v

    # actual payments must be positive
    @validator('actualPayments')
    def positive_actual(cls, v):
        if v <= 0:
            raise ValueError('Actual Payments Must Be Positive')
        return v

    # minimum payments cannot be more than balance
    @validator('minPayment')
    def min_lt_balance(cls, v, values):
        if 'cardBalance' in values and v >= values['cardBalance']:
            raise ValueError('Minimum Payment Cannot Be Higher Than Balance')
        return v

    # maximum payments cannot be more than balance
    @validator('maxPayment')
    def max_lt_balance(cls, v, values):
        if 'cardBalance' in values and v >= values['cardBalance']:
            raise ValueError('Maximum Payment Cannot Be Higher Than Balance')
        return v

    # actual payments cannot be more than balance
    @validator('actualPayments')
    def act_lt_balance(cls, v, values):
        if 'cardBalance' in values and v >= values['cardBalance']:
            raise ValueError('Actual Payment Cannot Be Higher Than Balance')
        return v

    # max payment must not be less than minimum payment
    @validator('maxPayment')
    def max_bg_min(cls, v, values):
        if 'minPayment' in values and v < values['minPayment']:
            raise ValueError('Maximum Payment Cannot Be Less Than Minimum Payment')
        return v


class Model(BaseModel):
    budget: float
    cards: typing.List[Card]

    @validator('budget')
    def positive_budget(cls, v):
        if v <= 0:
            raise ValueError('Budget Must Be Positive')
        return v

    def update_payments(self):
        if all(card.actualProjections[-1] >= card.actualPayments for card in self.cards):
            return None

        overflow_money = sum(
            card.actualPayments - card.actualProjections[-1]
            for card in self.cards if card.actualProjections[-1] < card.actualPayments
        )

        card_orders = sorted(self.cards, key=lambda c: c.cardApr, reverse=True)
        for card in card_orders:
            # set this to the balance since it would be what is being paid
            if card.actualProjections[-1] < card.actualPayments:
                card.actualPayments = card.actualProjections[-1]
                # print(card.cardNickName, card.actualPayments)
                continue

            # if no money is left do nothing
            if overflow_money <= 0:
                continue

            if card.actualProjections[-1] < (card.actualPayments + overflow_money):
                to_add = card.actualProjections[-1] - card.actualPayments
            else:
                to_add = overflow_money

            overflow_money -= to_add
            card.actualPayments = card.actualPayments + to_add
            # print(card.cardNickName, to_add, overflow_money, card.actualPayments)

        return None


class UpdatedCard(BaseModel):
    cardNickName: str
    cardBalance: float
    cardApr: float
    minPayment: float
    maxPayment: float = None
    actualPayments: float = None
    suggestedPayment: float
    nextBalanceOnSuggested: float
    nextBalanceOnMin: float
    nextBalanceOnCurrentPayment: float


class ResponseModel(BaseModel):
    budget: float
    solution: str
    initialBalance: float
    endBalanceOnMinimumPayment: float
    endBalanceOnCurrentPayment: float
    endBalanceOnSuggestedPayment: float
    updatedCards: typing.List[UpdatedCard]


class CompareOptions(BaseModel):
    nextBalanceOnMin: float
    nextBalanceOnCurrentPayment: float
    nextBalanceOnSuggested: float


class CompareOptionsCard(BaseModel):
    cardNickName: str
    projection: typing.List[typing.Dict[str, CompareOptions]]


class CompareResponseModel(BaseModel):
    progress: typing.List[CompareOptionsCard]


@app.get("/")
async def read_root():
    return {
        "Message": "Welcome",
        "Objective": api_objective.strip()
    }


@app.post("/cards", response_model=ResponseModel)
async def suggest_payments(model: Model):
    budget = model.budget
    balances = tuple(card.cardBalance for card in model.cards)
    aprs = tuple(card.cardApr for card in model.cards)
    minimum_payments = tuple(card.minPayment for card in model.cards)
    maximum_payments = tuple(card.maxPayment for card in model.cards)
    actual_payments = tuple(card.actualPayments for card in model.cards)

    # if any actual payment is null then just make it the minimum payment
    actual_payments = tuple(map(lambda act, minp: minp if act is None else act, actual_payments, minimum_payments))

    # perform allocation
    (
        suggested_payments,
        on_mins,
        on_suggested,
        lp_status,
        _,
        on_actual
    ) = allocate(balances, aprs, minimum_payments, maximum_payments, budget, actual_payments)

    return_data = {
        'budget': model.budget,
        'solution': lp_status,
        'initialBalance': sum(balances),
        'endBalanceOnMinimumPayment': sum(on_mins),
        'endBalanceOnCurrentPayment': sum(on_actual),
        'endBalanceOnSuggestedPayment': sum(on_suggested)
    }

    updated_cards = []
    for card, payment, on_sugg, on_min, stusquo in zip(
            model.cards,
            suggested_payments,
            on_suggested,
            on_mins,
            on_actual
    ):
        dic = json.loads(card.json())
        dic.update(
            {
                'suggestedPayment': payment,
                'nextBalanceOnSuggested': on_sugg,
                'nextBalanceOnMin': on_min,
                'nextBalanceOnCurrentPayment': stusquo
            }
        )
        updated_cards.append(dic)

    return_data['updatedCards'] = updated_cards

    return return_data


@app.post("/cards/12", response_model=CompareResponseModel)
async def compare_12_months(model: Model):
    # cycle months
    current_month = months[datetime.date.today().month - 1]
    cycles = itertools.cycle(months)  # cycle the months
    cycles = itertools.dropwhile(lambda x: x != current_month, cycles)  # shift cycles til we reach current month
    cycles = tuple(next(cycles) for _ in range(13))  # next 12 months plus current

    # ensure card minimums are alright
    for card in model.cards:
        # make min balance if somehow min is sent as higher than balance
        card.update_min()

        # we get the rate to use to update interest
        card.min2balancerate = round(card.minPayment / card.cardBalance, 2)

        # create something to store the projections
        card.minProjections = [card.cardBalance]
        card.actualProjections = [card.cardBalance]

    # budget and balance data
    budget = model.budget
    balances = tuple(card.cardBalance for card in model.cards)
    aprs = tuple(card.cardApr for card in model.cards)
    minimum_payments = tuple(card.minPayment for card in model.cards)
    maximum_payments = tuple(card.maxPayment for card in model.cards)

    # min projections - easy so keep it apart
    for _ in range(1, 13):
        for card in model.cards:
            card.minPayment = card.minProjections[-1] * card.min2balancerate
            card.update_min()

            # calculation
            new_balance = balance_on_constant_pay(card.minProjections[-1], card.minPayment, card.cardApr, 1)
            new_balance = round(new_balance, 2)
            card.minProjections.append(new_balance)

    # actual projections
    for _ in range(1, 13):
        # after all cards processed update payments on the model
        model.update_payments()

        for card in model.cards:
            new_balance = balance_on_constant_pay(card.actualProjections[-1], card.actualPayments, card.cardApr, 1)
            new_balance = round(new_balance, 2)
            card.actualProjections.append(new_balance)

    min_projection = [card.minProjections for card in model.cards]
    actual_projection = [card.actualProjections for card in model.cards]

    # projections on optimal payment month in month out
    optimal_monthly, new_balance = [balances], balances
    for _ in range(13):
        new_balance = allocate(new_balance, aprs, minimum_payments, maximum_payments, budget=budget, solution_only=True)
        new_balance = tuple(round(el, 4) for el in new_balance)
        optimal_monthly.append(new_balance)

    optimal_monthly = zip(*optimal_monthly)

    projections = (tuple(zip(*el)) for el in zip(min_projection, actual_projection, optimal_monthly))
    projections = (
        [
            dict(nextBalanceOnMin=a, nextBalanceOnCurrentPayment=b, nextBalanceOnSuggested=c)
            for a, b, c in projection
        ] for projection in projections
    )

    """
    When one card has a balance low enough that payment can be reallocated to another card we go directly to the
    card with the highest APR
    """

    response = []
    for card, projection in zip(model.cards, projections):
        dic = dict(cardNickName=card.cardNickName)
        dic["projection"] = [{el[0]: el[1]} for el in zip(cycles, projection)]
        response.append(dic)

    return {"progress": response}


TP = typing.Tuple[float, ...]


@functools.lru_cache(maxsize=64)
def balance_on_constant_pay(balance: float, payment: float, rate: float, n: int):
    """

    :param balance:
    :param payment:
    :param rate:
    :param n:
    :return:
    """
    balance_portion = (balance * (1 + rate / 12 / 100) ** n)
    payment_portion = (payment * sum((1 + rate / 12 / 100) ** i for i in range(1, n + 1)))
    return max(0.0, balance_portion - payment_portion)


def allocate(balances: TP, aprs: TP, minimum_payments_: TP, maximum_payments_: TP, budget: float,
             actual_payments: TP = None, solution_only: bool = False):
    """

    :param balances:
    :param aprs:
    :param minimum_payments_:
    :param maximum_payments_:
    :param budget:
    :param actual_payments:
    :param solution_only:
    :return:
    """
    # The problem
    problem = pulp.LpProblem("InterestMin", pulp.LpMaximize)

    # update minimum payment if it is more than the balance
    minimum_payments_ = tuple(min(el) for el in zip(balances, minimum_payments_))

    # update maximum payment - it cannot be more than the balance but it cannot be less than minimum payment
    maximum_payments_ = tuple(min(el) if el[1] else el[0] for el in zip(balances, maximum_payments_))
    maximum_payments_ = tuple(max(el) for el in zip(minimum_payments_, maximum_payments_))

    # update actual payments too - assumption is very simple: if you don't have anything to pay you won't pay
    # this doesn't handle how you would reallocate your budget
    if actual_payments:
        actual_payments = tuple(min(el) for el in zip(balances, actual_payments))

    # we can only assume a limited number of cards for now
    payments = [pulp.LpVariable(string.ascii_letters[i], minimum_payments_[i], maximum_payments_[i]) for i in
                range(len(balances))]

    # constraint
    budget_constraint = sum(payments) <= budget

    # objective function - less accrued interest with payments as opposed to minimum payments
    balances_minus_payments = map(lambda bal, pymt: bal - pymt, balances, payments)
    balances_minus_minimum_payments = map(lambda bal, pymt: bal - pymt, balances, minimum_payments_)

    # TODO - simplify the objective function - although that is already done by the package
    interests = tuple(el / 100 for el in aprs)
    next_balances = tuple(map(lambda bal, r: bal * (1 + r / 12), balances_minus_payments, interests))
    next_balances_minimum_payments = tuple(
        map(lambda bal, r: bal * (1 + r / 12), balances_minus_minimum_payments, interests)
    )

    objective_function = sum(next_balances_minimum_payments) - sum(next_balances)

    # add constraint and objective function
    problem += budget_constraint
    problem += objective_function

    # solve
    problem.solve()

    # balances after suggested payment
    next_balances = tuple(el.value() for el in next_balances)

    # just to see what the balance will be next month
    if solution_only:
        return next_balances

    # optimal status?
    solution_status = pulp.LpStatus[problem.status]

    # optimal interest saved
    money_saved = pulp.value(problem.objective)

    # values of the variables
    solved_values = tuple(el.varValue for el in payments)

    # balance with actual balance
    if actual_payments:
        balances_minus_actual_payments = map(lambda bal, pymt: bal - pymt, balances, actual_payments)
        balance_on_actual = tuple(
            map(lambda bal, r: bal * (1 + r / 12), balances_minus_actual_payments, interests)
        )
    else:
        balance_on_actual = (None,) * len(balances)

    return (
        solved_values,
        next_balances_minimum_payments,
        next_balances,
        solution_status,
        money_saved,
        balance_on_actual
    )
