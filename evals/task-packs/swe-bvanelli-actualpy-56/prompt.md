# Bug fix: bvanelli/actualpy

You are fixing a real bug in the open-source repository `bvanelli/actualpy` at commit `2ad5f638789af3e37a3a07ed3f4d4938a8209ed4`.

## Issue

Operation ActionType.SET_SPLIT_AMOUNT not supported
### Description

I've a rule that given a certain payee, it creates a split transaction of 50% each.
it seems that the code here is not supporting it.
is there a way to support this or a hint on how i can create a pr?

Interface / API notes:
Method: ActionType.SET_SPLIT_AMOUNT
Location: actual.rules (enum ActionType)
Inputs: None (enum member)
Outputs: Enum value representing the “set‑split‑amount” operation (string value `"set-split-amount"`). Used by Action.op to trigger split‑amount handling.

Method: Condition.get_value(self) → Any
Location: actual.rules (class Condition)
Inputs: self – a Condition instance whose .value may be any type (including None).
Outputs: Returns the stored .value, preserving None (i.e., returns None when the condition value is None). Allows tests to safely query a condition’s value without raising.

Method: Rule.set_split_amount(self, transaction: Transactions) → list[Transactions]
Location: actual.rules (class Rule)
Inputs:
- transaction (Transactions): a parent transaction that has no existing splits and is not a child split.
Outputs:
- A list of newly created split Transactions ordered as specified by the rule’s Action objects.
- May raise ActualSplitTransactionError if the sum of split amounts does not equal the parent amount.

Method: ActualSplitTransactionError
Location: actual.exceptions (class)
Inputs: inherits any arguments passed to ActualError.
Outputs: Exception instance signalling that the split‑transaction amounts are inconsistent. Tests expect this error when the internal sum function is mocked to break amount validation.

Function: Action.run(self, transaction: Transactions) → None
Location: actual.rules (class Action)
Inputs:
- transaction (Transactions): the target transaction (or the specific split when options `splitIndex` is provided).
- self.op may be ActionType.SET_SPLIT_AMOUNT, in which case the method does **not** perform the split itself (split handling is done in Rule.set_split_amount); otherwise it sets the appropriate field/value (including handling of splitIndex).
Outputs: Mutates the given transaction (or its split) in‑place; no return value.

## Task

Modify the python source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.
