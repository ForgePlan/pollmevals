# Bug fix: dtolnay/cxx

You are fixing a real bug in the open-source repository `dtolnay/cxx` at commit `c5f472ef62f6307521cb1fe8a76a204438a6eee0`.

## Issue

CxxVector::push_back
Adding push_back/pop functionality (and other mutation functionality) to `CxxVector` would be helpful for `CxxVector`s containing types that rust can obtain (e.g. `CxxVector<CxxString>` or `CxxVector<SharedPtr<T>>`). Similarly, `CxxVector::new()` or `CxxVector::default()` would be helpful to create them from Rust.

Interface / API notes:
Method: CxxVector<T>.push(self: Pin<&mut Self>, value: T)  
Location: src/cxx_vector.rs (impl block for CxxVector)  
Inputs: a pinned mutable reference to a CxxVector holding a trivial extern type `T` (e.g., `f64`, `Shared`), and an owned `value` of type `T`. `T` must satisfy `ExternType<Kind = Trivial>`.  
Outputs: `()` – the call mutates the underlying C++ `std::vector<T>` by appending the element; no return value.  
Description: Appends `value` to the back of the vector. The method creates a `ManuallyDrop<T>` wrapper, then forwards to the hidden FFI routine `__push_back`, which invokes C++ `std::vector::push_back` and destroys the temporary on the Rust side. Use it when you need to grow a `CxxVector` from Rust with element types that can be passed by value.

## Task

Modify the rust source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.
