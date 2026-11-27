; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Int)
(declare-fun y () Int)
(declare-fun w () Int)
(declare-fun old () Int)
(assert
 (>= x 0))
(assert
 (>= y 0))
(assert
 (>= w 0))
(assert
 (>= old 0))
(assert
 (let ((?x14 (+ old x)))
 (let ((?x15 (+ ?x14 y)))
 (let ((?x16 (+ ?x15 w)))
 (<= ?x16 9223372036854775807)))))
(assert
 (let ((?x20 (+ (+ x y) w)))
(let ((?x21 (+ old ?x20)))
(let ((?x14 (+ old x)))
(let ((?x15 (+ ?x14 y)))
(let ((?x16 (+ ?x15 w)))
(let (($x22 (= ?x16 ?x21)))
(not $x22))))))))
(check-sat)
