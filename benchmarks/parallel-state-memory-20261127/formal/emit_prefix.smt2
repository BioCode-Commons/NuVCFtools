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
 (< emitted submitted))
(assert
 (let ((?x799 (- submitted emitted)))
(let ((?x826 (- ?x799 1)))
(let (($x827 (<= ?x826 workers)))
(let ((?x823 (+ emitted 1)))
(let (($x825 (<= ?x823 submitted)))
(let (($x824 (>= ?x823 0)))
(let (($x828 (and $x824 $x825 $x827)))
(not $x828)))))))))
(check-sat)
