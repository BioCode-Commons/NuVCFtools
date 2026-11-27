; benchmark generated from python API
(set-info :status unknown)
(declare-fun C () String)
(declare-fun B () String)
(declare-fun A () String)
(assert
 (let ((?x185 (str.++ A (str.++ B C))))
(let (($x710 (= (str.++ (str.++ A B) C) ?x185)))
(not $x710))))
(check-sat)
