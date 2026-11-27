; benchmark generated from python API
(set-info :status unknown)
(declare-fun pending_line () (Seq Int))
(declare-fun reference_consumed () (Seq Int))
(declare-fun optimized_consumed () (Seq Int))
(declare-fun byte () Int)
(assert
 (let ((?x10 (seq.++ reference_consumed pending_line)))
 (= optimized_consumed ?x10)))
(assert
 (>= byte 0))
(assert
 (<= byte 255))
(assert
 (let ((?x24 (seq.len optimized_consumed)))
(let ((?x10 (seq.++ reference_consumed pending_line)))
(let ((?x23 (seq.len ?x10)))
(let (($x25 (= ?x23 ?x24)))
(let (($x22 (= ?x10 optimized_consumed)))
(let (($x26 (and $x22 $x25)))
(not $x26))))))))
(check-sat)
