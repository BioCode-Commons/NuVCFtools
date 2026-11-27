; benchmark generated from python API
(set-info :status unknown)
(declare-fun earlier_map () (Array String Int))
(declare-fun reference_map () (Array String Int))
(declare-fun earlier_count () Int)
(declare-fun reference_count () Int)
(declare-fun key () String)
(declare-fun current_count () Int)
(declare-fun current_map () (Array String Int))
(assert
 (= reference_map earlier_map))
(assert
 (= reference_count earlier_count))
(assert
 (let ((?x22 (select earlier_map key)))
(let ((?x21 (select reference_map key)))
(let (($x23 (and (distinct ?x21 ?x22) true)))
(let (($x19 (and (= current_map earlier_map) (= current_count earlier_count))))
(let (($x16 (and (= current_map reference_map) (= current_count reference_count))))
(let (($x20 (and (distinct $x16 $x19) true)))
(or $x20 $x23))))))))
(check-sat)
