; benchmark generated from python API
(set-info :status unknown)
(declare-fun e0 () Int)
(declare-fun e1 () Int)
(declare-fun e2 () Int)
(assert
 (>= e0 0))
(assert
 (>= e1 0))
(assert
 (>= e2 0))
(assert
 (let ((?x265 (+ (+ e0 e1) e2)))
 (<= ?x265 2)))
(assert
 (let (($x186 (= e2 0)))
(let (($x772 (= e1 0)))
(let (($x112 (= e0 0)))
(let (($x261 (or $x112 $x772 $x186)))
(not $x261))))))
(check-sat)
