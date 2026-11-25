/-!
# Doubling

The one definition the parity proofs are built on, and what is proved of it.
-/

namespace Proofs

/-- Twice a number. -/
def double (n : Nat) : Nat := n + n

theorem double_zero : double 0 = 0 := rfl

theorem double_eq_two_mul (n : Nat) : double n = 2 * n := by
  unfold double
  omega

theorem double_add (m n : Nat) : double (m + n) = double m + double n := by
  unfold double
  omega

end Proofs
