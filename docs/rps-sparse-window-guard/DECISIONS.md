- Decision: Treat date coverage as a property of every trading date used in MA/RPS windows, not only the final reference date.
- Reason: A full latest date is not enough when the trailing MA window still includes sparse partial-refresh dates that collapse the eligible universe.

- Decision: Reject undersized cache entries for otherwise healthy reference dates.
- Reason: The current `rps_cache` can preserve a bad 86-symbol computation for `2026-04-13` and keep poisoning later runs.
