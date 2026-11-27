; benchmark generated from python API
(set-info :status unknown)
(declare-fun workers () Int)
(declare-fun emitted () Int)
(declare-fun submitted () Int)
(assert
 (let (($x803 (>= workers 1)))
 (let ((?x799 (- submitted emitted)))
 (let (($x809 (<= ?x799 workers)))
 (let (($x800 (<= emitted submitted)))
 (let (($x499 (>= emitted 0)))
 (and $x499 $x800 $x809 $x803)))))))
(assert
 (let ((?x799 (- submitted emitted)))
 (< ?x799 workers)))
(assert
 (let ((?x956 (+ submitted 1)))
(let ((?x445 (- ?x956 emitted)))
(let (($x454 (<= ?x445 workers)))
(let (($x957 (<= emitted ?x956)))
(let (($x478 (and $x957 $x454)))
(not $x478)))))))
(check-sat)
