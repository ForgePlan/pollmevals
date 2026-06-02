# Bug fix: rust-bitcoin/rust-bitcoin

You are fixing a real bug in the open-source repository `rust-bitcoin/rust-bitcoin` at commit `db37bd27a105006980e5a4788acc23c6de9225df`.

## Issue

`Script::dust_value` method name disagrees with the documentation
Dust is a value that is not economically spendable and can not be broadcasted. The method is called `dust_value` which suggest it returns a value that is too small (and always returning 0 would be a valid implementation) but the documentation says "Returns the **minimum value* an output with this script should have in order **to be broadcastable** on today’s Bitcoin network." (emphasis mine) which implies it's a non-dust value.

Since writing a method that always returns 0 is useless I assume the documentation is right but the method is named incorrectly. I was not able to verify the implementation yet.

Interface / API notes:
Method: Script.minimal_non_dust(&self)
Location: impl Script in bitcoin::blockdata::script::borrowed.rs
Inputs: self – a reference to the Script whose dust threshold is being queried.
Outputs: crate::Amount – the minimum value an output with this script must have to be non‑dust, calculated using the default dust‑relay‑fee (3 sat/vByte).
Description: Returns the smallest spendable output value for the script under the default Bitcoin Core dust‑relay‑fee policy.

Method: Script.minimal_non_dust_custom(&self, dust_relay_fee: FeeRate)
Location: impl Script in bitcoin::blockdata::script::borrowed.rs
Inputs: self – a reference to the Script; dust_relay_fee – a FeeRate specifying the dust‑relay‑fee to use for the calculation.
Outputs: crate::Amount – the minimum non‑dust output value for the script using the supplied fee rate.
Description: Computes the minimal non‑dust amount for the script, allowing callers to provide a custom dust‑relay‑fee via a FeeRate.

## Task

Modify the rust source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.
