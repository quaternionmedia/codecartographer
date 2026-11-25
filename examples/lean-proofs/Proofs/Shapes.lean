import Proofs.Basic

/-!
# Shapes

Data rather than proof: a structure and one that extends it, an inductive
whose constructors carry arguments and one whose constructors carry none, a
class and its instances, and two axioms with a theorem that rests on them.
-/

namespace Proofs

/-- A point on the grid. -/
structure Point where
  x : Nat
  y : Nat
  deriving Repr

inductive Colour where
  | red | green | blue
  deriving Repr, DecidableEq

structure ColouredPoint extends Point where
  colour : Colour
  deriving Repr

inductive Shape where
  | circle (centre : Point) (radius : Nat)
  | rect (corner : Point) (width height : Nat)
  deriving Repr

/-- Something with a size. -/
class Sized (α : Type) where
  size : α → Nat

instance : Sized Point where
  size p := p.x + p.y

def Shape.area : Shape → Nat
  | .circle _ r => 3 * r * r
  | .rect _ w h => w * h

instance : Sized Shape where
  size := Shape.area

theorem Shape.area_rect (p : Point) (w h : Nat) : (Shape.rect p w h).area = w * h := rfl

theorem Shape.area_square (p : Point) (w : Nat) :
    (Shape.rect p w w).area + (Shape.rect p w w).area = double (w * w) := rfl

/-- The length one grid step stands for. Nothing here says what it is. -/
axiom unitLength : Nat

axiom unitLength_pos : 0 < unitLength

theorem scaled_pos (n : Nat) (h : 0 < n) : 0 < n * unitLength :=
  Nat.mul_pos h unitLength_pos

end Proofs
