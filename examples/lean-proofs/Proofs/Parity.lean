import Proofs.Basic

/-!
# Even and odd

Both are stated through `double`, so every proof here cites a lemma of
`Proofs.Basic`. The last theorem is left unfinished.
-/

namespace Proofs

/-- A number is even when it is the double of another. -/
def IsEven (n : Nat) : Prop := ∃ k, n = double k

/-- A number is odd when it is one more than a double. -/
def IsOdd (n : Nat) : Prop := ∃ k, n = double k + 1

theorem isEven_zero : IsEven 0 := ⟨0, double_zero.symm⟩

theorem isEven_double (n : Nat) : IsEven (double n) := ⟨n, rfl⟩

theorem IsEven.add {m n : Nat} (hm : IsEven m) (hn : IsEven n) : IsEven (m + n) := by
  obtain ⟨a, ha⟩ := hm
  obtain ⟨b, hb⟩ := hn
  exact ⟨a + b, by rw [ha, hb, double_add]⟩

theorem IsOdd.succ_of_even {n : Nat} (h : IsEven n) : IsOdd (n + 1) := by
  obtain ⟨k, hk⟩ := h
  exact ⟨k, by rw [hk]⟩

/-- Every number is even or odd. The inductive step is left open. -/
theorem even_or_odd (n : Nat) : IsEven n ∨ IsOdd n := by
  induction n with
  | zero => exact Or.inl isEven_zero
  | succ n ih => sorry

end Proofs
