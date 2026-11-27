; benchmark generated from python API
(set-info :status unknown)
(declare-fun reference_prefix_length () Int)
(declare-fun pending () Bool)
(assert
 (let (($x13 (= reference_prefix_length 1)))
 (let (($x14 (= pending $x13)))
 (let (($x12 (<= reference_prefix_length 1)))
 (let (($x10 (>= reference_prefix_length 0)))
 (and $x10 $x12 $x14))))))
(assert
 (let ((?x24 (seq.unit 13)))
(let ((?x211 (ite pending ?x24 (as seq.empty (Seq Int)))))
(let ((?x210 (seq.extract ?x24 0 reference_prefix_length)))
(let (($x77 (= ?x210 ?x211)))
(not $x77))))))
(check-sat)
