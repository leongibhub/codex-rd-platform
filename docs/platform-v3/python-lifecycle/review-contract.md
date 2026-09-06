# 真实独立评审与Gate推进合同

状态：评审范围BASELINED，评审结论PENDING。本文没有预置review PASS。

Reviewer须由root实际派发，身份不同于harness developer与应用test_execution执行者。在同一隔离数据库使用真实host actor注册reviewer，再领取G8评审工作；仅注册姓名不能视为完成评审。审查原始源码/Git摘要、文档、需求/NFR覆盖、case定义、真实stdout/stderr与断言、缺陷及未执行项后再登记结果。

需要的评审项目：G3 requirement_review（来源/假设/测量标准与RTM）；G4 architecture_review（模块、数据、错误、安全和部署边界与源码吻合）；G8 code_review、architecture_conformance、security_regression_risks、classified_findings（包括harness实际改动和已分类未解决发现）。任何不符合项保留真实severity/状态，不能用空列表假装已审。

review EVD必须已经由实际reviewer登记：kind=review、status=VERIFIED、source.kind=host、source.actor为该真实身份；metadata必须包含subject_id、result、gate_ids或gate_id、criteria、artifact_refs。artifact_refs至少锁定全部7条REQ/NFR、DES-PLC-001、CODE-MATRIX-PYTHON-EXPENSES和DOC-PLC-REVIEW-SCOPE；实际报告中的证据/用例版本也应锁定。记录时间必须是实际观察时间，locator指向真实报告文件及摘要，或其实际完整内容。结果不是PASS时不使用PASS模板。

脚本导出的promotion-plan.json是请求说明，不是审批：

```python
assessment = runtime.execute('gate.assess', {'project_id': actual_project_id, 'gate_id': actual_gate_id})
# Reviewer必须读取assessment并作出真实决定。仅当其结论与candidate都为PASS时：
decision_evidence = runtime.execute('evidence.register', {
    'project_id': actual_project_id, 'kind': 'gate_decision', 'status': 'VERIFIED',
    'source': {'kind': 'host', 'actor': actual_reviewer_id},
    'observed_at': actual_observation_timestamp,
    'locator': actual_reviewed_decision_record,
    'metadata': {'assessment_id': assessment['id'], 'status': actual_decision,
                 'artifact_refs': actual_subject_versions}
})
runtime.execute('gate.decide', {
    'assessment_id': assessment['id'], 'status': actual_decision,
    'decided_by': actual_reviewer_id,
    'decision_evidence_refs': [{'type':'EVIDENCE','id':decision_evidence['id'],'version':1}]
})
```

FAIL/BLOCKED决定必须补真实reason/resolution，并遵守Runtime校验。不要创建合成身份服务来满足G9；此项目没有真实人类批准provider、验收结果或部署事实。

finalize消费已有review EVD ID清单和当前有效G0–G8决定；它不能创建评审或Gate决定。缺项以PENDING及具体理由报告，不能把脚本退出0解释为项目全生命周期完成。
