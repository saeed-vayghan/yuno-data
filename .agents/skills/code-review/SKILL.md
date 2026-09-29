---
name: code-review
description: Reviews TypeScript code using functional programming principles. Use when reviewing TypeScript code or PRs.
---

# TypeScript FP Code Review Guide

When you review TypeScript code, check it using a functional programming (FP) mindset. Apply these guidelines to domain and business logic (the functional core). I/O, framework glue, and startup code form the thin shell, where side effects and throwing on fatal config errors are expected, so don't flag them there.

## 1. Avoid Changing State (Immutability)
*   **Use `const` and `readonly`:** Do not reassign variables. Mark array and object inputs as `readonly` (for example, `readonly string[]` or `Readonly<Todo>`).
*   **Do not mutate data:** Do not use mutating methods like `.push()`, `.pop()`, or directly changing object properties. Instead, return new copies using the spread operator (`...`) or non-mutating methods like `.map()`, `.filter()`, and `.concat()`.

## 2. Write Pure Functions
*   **No side effects:** A function should only calculate its output based on its inputs. It must not change global variables, write to files, or modify external state directly.
*   **Predictable behavior:** Running the same function with the same inputs must always return the same result.

## 3. Keep Types Safe and Strict
*   **No `any`:** Avoid using `any`. Use `unknown` or specific type unions instead.
*   **Avoid type assertions:** Try not to use `as SomeType`. Let TypeScript infer types, or define them explicitly on functions and variables.
*   **Handle `null` and `undefined`:** Make sure all optional properties and nullish values are checked safely (using optional chaining `?.` or nullish coalescing `??`).

## 4. Prefer Expressions Over Statements
*   **No imperative loops:** Avoid `for` and `while` loops. Use array methods like `.map()`, `.filter()`, and `.reduce()` to transform data.
*   **Avoid reassigning variables:** Instead of using `let` with `if/else` statements to set a value, use ternary operators (`cond ? a : b`) or helper functions.

## 5. Handle Errors Safely
*   **Avoid throwing exceptions:** Instead of throwing exceptions that crash the program, prefer returning a status object (like `{ success: true, data: T } | { success: false, error: Error }`).

---

## How to Give Feedback
*   Show the code change you suggest.
*   Explain the functional programming benefit (e.g., "This avoids side effects" or "This keeps types safe").
*   Keep your tone helpful, clear, and simple.