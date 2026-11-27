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
 (let ((?x15 (seq.unit byte)))
(let ((?x16 (seq.++ pending_line ?x15)))
(let (($x13 (= byte 10)))
(let ((?x17 (ite $x13 (as seq.empty (Seq Int)) ?x16)))
(let ((?x10 (seq.++ reference_consumed pending_line)))
(let ((?x14 (ite $x13 ?x10 reference_consumed)))
(let ((?x20 (seq.++ ?x14 ?x17)))
(let ((?x19 (ite $x13 optimized_consumed (seq.++ optimized_consumed ?x15))))
(let (($x21 (= ?x19 ?x20)))
(not $x21)))))))))))
(check-sat)
