from debt_display_strategies import DebtDisplayStrategy
from debt_display_strategies.aggregation_by_dates import AggregationByDates
from debt_display_strategies.aggregation_by_people import AggregationByPeople


class DebtDisplayHandler:
    def __init__(self, strategy: DebtDisplayStrategy = None):
        if strategy is None:
            strategy = AggregationByPeople()
        self.strategy = strategy

    def current_strategy(self) -> str:
        if isinstance(self.strategy, AggregationByDates):
            return 'aggregation_by_dates'
        elif isinstance(self.strategy, AggregationByPeople):
            return 'aggregation_by_people'

    def get_unpaid_shifts_message(self) -> str:
        return self.strategy.get_unpaid_shifts_message()

    def get_next_payment_message(self, offset=0) -> [str, dict]:
        return self.strategy.get_next_payment_message(offset)

    def mark_shift_as_paid(self, current_debt: dict) -> None:
        self.strategy.mark_shift_as_paid(current_debt)