# 实际逐需求测试报告

本次实际Tester: /root/v3_qa_platform

```json
{
  "report_scope": "LIFECYCLE_DECLARED_TEST_SCOPE",
  "project_id": "project-337a2843b20e407981e60c2a28c605e4",
  "generated_at": "2026-09-06T10:29:18.054279+00:00",
  "software_versions": [],
  "test_environment": [
    {
      "id": "EVD-PLC-ENV",
      "kind": "test_environment",
      "locator": {
        "inline_json": {
          "build_directory": "D:\\codex-rd-platform\\.rd-platform\\python-lifecycle\\actual\\build",
          "host_assignment": "Codex root assigned v3_qa_platform independent TASK-V3-008 testing in current turn",
          "platform": "win32",
          "python": "3.13.5 (tags/v3.13.5:6cb20a2, Jun 11 2025, 16:15:46) [MSC v.1943 64 bit (AMD64)]",
          "source_hashes": {
            "examples/multistack/python_expenses/__pycache__/expense_analyzer.cpython-313.pyc": "7e4f6d031764d0e10e774cabf488fffb3577a9c63245509f0e49aa078dca8811",
            "examples/multistack/python_expenses/expense_analyzer.py": "e5b1fd29183b182d3288feba8168d7babb5112972d67493291f8d1694151193f",
            "examples/multistack/python_expenses/manifest.json": "34456a238a3e9ba1cfe495d4b3f2c7b958f597c6956afa94be58629e0c12fe90",
            "examples/multistack/python_expenses/tests/__pycache__/test_expense_analyzer.cpython-313.pyc": "ccbb49dfad612f2c5a0ec3ce0a395e95158631dc6110c5119acccd49ec466536",
            "examples/multistack/python_expenses/tests/test_expense_analyzer.py": "53016b1113237a79e928f2b92308a577856c6b4e8719d94e4b2d61ac76f5249d"
          }
        },
        "sha256": "85c90f944e6875abaf0af165686a1084edef897aa9e1eaa42ba45d934ffaf624"
      },
      "metadata": {
        "artifact_refs": [
          {
            "id": "CODE-MATRIX-PYTHON-EXPENSES",
            "type": "CODE_CHANGE",
            "version": 1
          }
        ],
        "criteria": [
          "test_environment"
        ],
        "gate_id": "G7"
      },
      "observed_at": "2026-09-06T10:28:32.951975+00:00",
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_at": "2026-09-06T10:28:32.957992+00:00",
      "recorded_by": "/root/v3_qa_platform",
      "recorded_role": "tester",
      "source": {
        "actor": "/root/v3_qa_platform",
        "kind": "host"
      },
      "status": "VERIFIED",
      "supersedes_id": null,
      "version": 1
    }
  ],
  "test_strategy": [
    {
      "artifact_id": "TM-PLC-001",
      "created_at": "2026-09-06T10:27:14.380985+00:00",
      "created_by": "/root/v3_skill_forward",
      "function_tree": {
        "expense_cli": [
          "CSV decode and shape",
          "business validation",
          "exact totals",
          "errors",
          "resource boundaries",
          "input integrity"
        ]
      },
      "id": "TM-PLC-001",
      "objects": [
        {
          "description": "Unmodified public CLI and actual existing unit suite",
          "object_id": "CLI"
        }
      ],
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-001",
          "type": "NFR",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-003",
          "type": "NFR",
          "version": 1
        }
      ],
      "risks": [
        {
          "description": "Valid UTF-8/BOM/reordered CSV accepted; malformed columns/rows rejected",
          "impact": "HIGH",
          "likelihood": "MEDIUM",
          "priority": "P0",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_id": "RISK-REQ-MATRIX-PY-01"
        },
        {
          "description": "Sorted category totals and exact Decimal strings in success JSON",
          "impact": "HIGH",
          "likelihood": "MEDIUM",
          "priority": "P0",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-02",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_id": "RISK-REQ-MATRIX-PY-02"
        },
        {
          "description": "Empty, malformed date/category/amount, negative and non-finite data rejected",
          "impact": "HIGH",
          "likelihood": "MEDIUM",
          "priority": "P0",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_id": "RISK-REQ-MATRIX-PY-03"
        },
        {
          "description": "Data/path errors exit 1 without success stdout; argument errors exit 2",
          "impact": "HIGH",
          "likelihood": "MEDIUM",
          "priority": "P0",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_id": "RISK-REQ-MATRIX-PY-04"
        },
        {
          "description": "Exact decimal value and JSON string representation inside supported limits",
          "impact": "HIGH",
          "likelihood": "MEDIUM",
          "priority": "P0",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-001",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_id": "RISK-NFR-MATRIX-PY-001"
        },
        {
          "description": "1000 significant digits, exponent -1000..1000 and 100000 rows are exact limits",
          "impact": "HIGH",
          "likelihood": "MEDIUM",
          "priority": "P0",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_id": "RISK-NFR-MATRIX-PY-002"
        },
        {
          "description": "Observed CLI input and application source remain unchanged; isolated build outputs",
          "impact": "HIGH",
          "likelihood": "MEDIUM",
          "priority": "P0",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-003",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_id": "RISK-NFR-MATRIX-PY-003"
        }
      ],
      "source": {
        "actor": "/root/v3_skill_forward",
        "kind": "host"
      },
      "state": "BASELINED",
      "status": "CURRENT",
      "test_points": [
        {
          "coverage_rule": "TC-PLC-UTF8: {\"csv\": \"﻿category,amount,date\\n餐饮,0.10,2026-09-06\\n餐饮,0.20,2026-09-06\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-UTF8",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-01"
          ],
          "type": "COMPATIBILITY"
        },
        {
          "coverage_rule": "TC-PLC-TOTAL: {\"csv\": \"date,category,amount\\n2026-09-06,z,2.00\\n2026-09-06,a,0.10\\n2026-09-06,a,0.20\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-TOTAL",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-02",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "NFR-MATRIX-PY-001",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-02",
            "RISK-NFR-MATRIX-PY-001"
          ],
          "type": "FUNCTIONAL"
        },
        {
          "coverage_rule": "TC-PLC-LONG: {\"csv\": \"date,category,amount\\n2026-09-06,a,9999999999999999999999999999\\n2026-09-06,a,2\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-LONG",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-02",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "NFR-MATRIX-PY-001",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-02",
            "RISK-NFR-MATRIX-PY-001"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-ZERO: {\"csv\": \"date,category,amount\\n2026-09-06,a,0\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-ZERO",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-02",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-02",
            "RISK-REQ-MATRIX-PY-03"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-HEADER-MISSING: {\"csv\": \"date,amount\\n2026-09-06,1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-HEADER-MISSING",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-01",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-HEADER-EXTRA: {\"csv\": \"date,category,amount,extra\\n2026-09-06,a,1,x\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-HEADER-EXTRA",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-01",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-HEADER-DUPLICATE: {\"csv\": \"date,date,amount\\n2026-09-06,a,1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-HEADER-DUPLICATE",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-01",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-ROW-MISSING: {\"csv\": \"date,category,amount\\n2026-09-06,a\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-ROW-MISSING",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-01",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-ROW-EXTRA: {\"csv\": \"date,category,amount\\n2026-09-06,a,1,x\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-ROW-EXTRA",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-01",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-ENCODING: {\"input_base64\": \"ZGF0ZSxjYXRlZ29yeSxhbW91bnQKMjAyNi0wOS0wNiz/LDEK\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-ENCODING",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-01",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-EMPTY: {\"csv\": \"\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-EMPTY",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-HEADER-ONLY: {\"csv\": \"date,category,amount\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-HEADER-ONLY",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-DATE-EMPTY: {\"csv\": \"date,category,amount\\n,a,1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-DATE-EMPTY",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-DATE-FORMAT: {\"csv\": \"date,category,amount\\n2026-9-6,a,1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-DATE-FORMAT",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-DATE-CALENDAR: {\"csv\": \"date,category,amount\\n2026-02-30,a,1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-DATE-CALENDAR",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-CATEGORY: {\"csv\": \"date,category,amount\\n2026-09-06, ,1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-CATEGORY",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-AMOUNT-EMPTY: {\"csv\": \"date,category,amount\\n2026-09-06,a,\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-AMOUNT-EMPTY",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-AMOUNT-TEXT: {\"csv\": \"date,category,amount\\n2026-09-06,a,abc\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-AMOUNT-TEXT",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-NEGATIVE: {\"csv\": \"date,category,amount\\n2026-09-06,a,-1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-NEGATIVE",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-NAN: {\"csv\": \"date,category,amount\\n2026-09-06,a,NaN\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-NAN",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-SNAN: {\"csv\": \"date,category,amount\\n2026-09-06,a,sNaN\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-SNAN",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-INFINITY: {\"csv\": \"date,category,amount\\n2026-09-06,a,Infinity\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-INFINITY",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-NEG-INFINITY: {\"csv\": \"date,category,amount\\n2026-09-06,a,-Infinity\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-NEG-INFINITY",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-MISSING-FILE: {\"missing_file\": true}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-MISSING-FILE",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-NO-ARG: {\"no_args\": true}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-NO-ARG",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-EXTRA-ARG: {\"extra_arg\": true}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-EXTRA-ARG",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-04"
          ],
          "type": "NEGATIVE"
        },
        {
          "coverage_rule": "TC-PLC-DIGITS-1000: {\"decimal_expected\": \"9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999\", \"csv\": \"date,category,amount\\n2026-09-06,a,9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-DIGITS-1000",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-DIGITS-1001: {\"csv\": \"date,category,amount\\n2026-09-06,a,99999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-DIGITS-1001",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-EXP-PLUS-1000: {\"decimal_expected\": \"1E+1000\", \"csv\": \"date,category,amount\\n2026-09-06,a,1E+1000\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-EXP-PLUS-1000",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-EXP-MINUS-1000: {\"decimal_expected\": \"1E-1000\", \"csv\": \"date,category,amount\\n2026-09-06,a,1E-1000\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-EXP-MINUS-1000",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-EXP-PLUS-1001: {\"decimal_expected\": null, \"csv\": \"date,category,amount\\n2026-09-06,a,1E+1001\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-EXP-PLUS-1001",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-EXP-MINUS-1001: {\"decimal_expected\": null, \"csv\": \"date,category,amount\\n2026-09-06,a,1E-1001\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-EXP-MINUS-1001",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-ROWS-100000: {\"rows\": 100000, \"decimal_expected\": \"100000\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-ROWS-100000",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-ROWS-100001: {\"rows\": 100001}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-ROWS-100001",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "BOUNDARY"
        },
        {
          "coverage_rule": "TC-PLC-INPUT-UNCHANGED-OK: {\"csv\": \"date,category,amount\\n2026-09-06,a,1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-INPUT-UNCHANGED-OK",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-003",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-003"
          ],
          "type": "DATA_CONSISTENCY"
        },
        {
          "coverage_rule": "TC-PLC-INPUT-UNCHANGED-ERROR: {\"csv\": \"date,category,amount\\n2026-09-06,a,-1\\n\"}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-INPUT-UNCHANGED-ERROR",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "NFR-MATRIX-PY-003",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-NFR-MATRIX-PY-003"
          ],
          "type": "DATA_CONSISTENCY"
        },
        {
          "coverage_rule": "TC-PLC-UNIT-SUITE: {\"unit_suite\": true}",
          "object_id": "CLI",
          "point_id": "TP-TC-PLC-UNIT-SUITE",
          "rationale": "Observe the exact named input partition",
          "requirement_refs": [
            {
              "id": "REQ-MATRIX-PY-01",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-02",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-03",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "REQ-MATRIX-PY-04",
              "type": "REQ",
              "version": 1
            },
            {
              "id": "NFR-MATRIX-PY-001",
              "type": "NFR",
              "version": 1
            },
            {
              "id": "NFR-MATRIX-PY-002",
              "type": "NFR",
              "version": 1
            }
          ],
          "risk_refs": [
            "RISK-REQ-MATRIX-PY-01",
            "RISK-REQ-MATRIX-PY-02",
            "RISK-REQ-MATRIX-PY-03",
            "RISK-REQ-MATRIX-PY-04",
            "RISK-NFR-MATRIX-PY-001",
            "RISK-NFR-MATRIX-PY-002"
          ],
          "type": "FUNCTIONAL"
        }
      ],
      "types": [
        "BOUNDARY",
        "COMPATIBILITY",
        "DATA_CONSISTENCY",
        "FUNCTIONAL",
        "NEGATIVE"
      ],
      "version": 1
    }
  ],
  "total": 37,
  "executed": 37,
  "counts": {
    "PASS": 37,
    "FAIL": 0,
    "BLOCKED": 0,
    "NOT_EXECUTED": 0
  },
  "pass_rate": 1.0,
  "complete_snapshot": true,
  "collection_counts": {
    "gates": 12,
    "work_orders": 2,
    "artifacts": 23,
    "trace_links": 161,
    "test_models": 1,
    "test_cases": 37,
    "test_executions": 37,
    "defects": 0,
    "gate_assessments": 0,
    "gate_decisions": 0,
    "evidence": 45,
    "releases": 0
  },
  "historical_execution_counts": {
    "PASS": 37
  },
  "test_types": {
    "FUNCTIONAL": {
      "cases": 2,
      "status": "PASS"
    },
    "NEGATIVE": {
      "cases": 22,
      "status": "PASS"
    },
    "BOUNDARY": {
      "cases": 10,
      "status": "PASS"
    },
    "PERFORMANCE": {
      "cases": 0,
      "status": "NOT_EXECUTED"
    },
    "STRESS": {
      "cases": 0,
      "status": "NOT_EXECUTED"
    },
    "STABILITY": {
      "cases": 0,
      "status": "NOT_EXECUTED"
    },
    "COMPATIBILITY": {
      "cases": 1,
      "status": "PASS"
    },
    "SECURITY": {
      "cases": 0,
      "status": "NOT_EXECUTED"
    },
    "RECOVERY": {
      "cases": 0,
      "status": "NOT_EXECUTED"
    },
    "DATA_CONSISTENCY": {
      "cases": 2,
      "status": "PASS"
    }
  },
  "case_results": [
    {
      "case_id": "TC-PLC-UTF8",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "COMPATIBILITY",
      "result": "PASS",
      "execution_id": "execution-4bac56f547804c93b8a09043235393c8",
      "evidence_refs": [
        {
          "id": "EVD-execution-4bac56f547804c93b8a09043235393c8",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-TOTAL",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-001",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "FUNCTIONAL",
      "result": "PASS",
      "execution_id": "execution-0ad6ae01f6634090bf184bb021978e60",
      "evidence_refs": [
        {
          "id": "EVD-execution-0ad6ae01f6634090bf184bb021978e60",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-LONG",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-001",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-dda65f9c074c43d4879a177b6ef98485",
      "evidence_refs": [
        {
          "id": "EVD-execution-dda65f9c074c43d4879a177b6ef98485",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-ZERO",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-446b04cd254241979f2e2e050d3abe36",
      "evidence_refs": [
        {
          "id": "EVD-execution-446b04cd254241979f2e2e050d3abe36",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-HEADER-MISSING",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-ddba8635d4ce47f79af52d40778c7c70",
      "evidence_refs": [
        {
          "id": "EVD-execution-ddba8635d4ce47f79af52d40778c7c70",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-HEADER-EXTRA",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-bf44ead6c482444d9ea45193fefbd12e",
      "evidence_refs": [
        {
          "id": "EVD-execution-bf44ead6c482444d9ea45193fefbd12e",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-HEADER-DUPLICATE",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-16d1bf2e678d4700bb4fb0e339d1f7c1",
      "evidence_refs": [
        {
          "id": "EVD-execution-16d1bf2e678d4700bb4fb0e339d1f7c1",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-ROW-MISSING",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-c56ea2af6d9743abae943067f555bdda",
      "evidence_refs": [
        {
          "id": "EVD-execution-c56ea2af6d9743abae943067f555bdda",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-ROW-EXTRA",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-9c05bfdcecff461cb5dff97fc8601ebc",
      "evidence_refs": [
        {
          "id": "EVD-execution-9c05bfdcecff461cb5dff97fc8601ebc",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-ENCODING",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-7a6e2f2e6cc04231bd4da22348a5cb62",
      "evidence_refs": [
        {
          "id": "EVD-execution-7a6e2f2e6cc04231bd4da22348a5cb62",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-EMPTY",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-98e8a0fef38d4be9bf2e00f7c2b21217",
      "evidence_refs": [
        {
          "id": "EVD-execution-98e8a0fef38d4be9bf2e00f7c2b21217",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-HEADER-ONLY",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-cc28a3acebc141439d456ab85ae6b2f2",
      "evidence_refs": [
        {
          "id": "EVD-execution-cc28a3acebc141439d456ab85ae6b2f2",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-DATE-EMPTY",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-49d6a2e8d74c4c54a10f72ec0b5c29b6",
      "evidence_refs": [
        {
          "id": "EVD-execution-49d6a2e8d74c4c54a10f72ec0b5c29b6",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-DATE-FORMAT",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-1fa83a3f25c14d12b877f810ceb489eb",
      "evidence_refs": [
        {
          "id": "EVD-execution-1fa83a3f25c14d12b877f810ceb489eb",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-DATE-CALENDAR",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-08add237b82e4c2d8e2d00118ec2f855",
      "evidence_refs": [
        {
          "id": "EVD-execution-08add237b82e4c2d8e2d00118ec2f855",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-CATEGORY",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-8f3c514fb8014d40ba9ada89db961a22",
      "evidence_refs": [
        {
          "id": "EVD-execution-8f3c514fb8014d40ba9ada89db961a22",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-AMOUNT-EMPTY",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-d8cd9e1a1b8147d78585fda242128d58",
      "evidence_refs": [
        {
          "id": "EVD-execution-d8cd9e1a1b8147d78585fda242128d58",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-AMOUNT-TEXT",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-2a5587a2450a46b2ba8e9a11018f97b1",
      "evidence_refs": [
        {
          "id": "EVD-execution-2a5587a2450a46b2ba8e9a11018f97b1",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-NEGATIVE",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-da308631e1764b919b059acf0281c1cc",
      "evidence_refs": [
        {
          "id": "EVD-execution-da308631e1764b919b059acf0281c1cc",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-NAN",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-ea25d84b6cf3404cb9938d6de44a1e9f",
      "evidence_refs": [
        {
          "id": "EVD-execution-ea25d84b6cf3404cb9938d6de44a1e9f",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-SNAN",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-69ce1a9e6ba94484867f65461bcd55b6",
      "evidence_refs": [
        {
          "id": "EVD-execution-69ce1a9e6ba94484867f65461bcd55b6",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-INFINITY",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-e5da8cc9584043d8a119ea730130b6d2",
      "evidence_refs": [
        {
          "id": "EVD-execution-e5da8cc9584043d8a119ea730130b6d2",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-NEG-INFINITY",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-d7bcdd8749f4410a8d30c907713ec01b",
      "evidence_refs": [
        {
          "id": "EVD-execution-d7bcdd8749f4410a8d30c907713ec01b",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-MISSING-FILE",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-60a31b2547cc49118cbb2799bf3e3e9b",
      "evidence_refs": [
        {
          "id": "EVD-execution-60a31b2547cc49118cbb2799bf3e3e9b",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-NO-ARG",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-5da7ccb093c7489782c1ba139d5d2610",
      "evidence_refs": [
        {
          "id": "EVD-execution-5da7ccb093c7489782c1ba139d5d2610",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-EXTRA-ARG",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "test_type": "NEGATIVE",
      "result": "PASS",
      "execution_id": "execution-f41db15aa78045beb3107678eda1cd93",
      "evidence_refs": [
        {
          "id": "EVD-execution-f41db15aa78045beb3107678eda1cd93",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-DIGITS-1000",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-4cc30c9d0d314e73b10a2f65a849009a",
      "evidence_refs": [
        {
          "id": "EVD-execution-4cc30c9d0d314e73b10a2f65a849009a",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-DIGITS-1001",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-415cbf55c93a4a88a1c30b9b8463e9bf",
      "evidence_refs": [
        {
          "id": "EVD-execution-415cbf55c93a4a88a1c30b9b8463e9bf",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-EXP-PLUS-1000",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-bfcf1e0e4d7242b0a41c2d1554708f24",
      "evidence_refs": [
        {
          "id": "EVD-execution-bfcf1e0e4d7242b0a41c2d1554708f24",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-EXP-MINUS-1000",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-87bb2fa37b84412b9a87b15f6b7f0224",
      "evidence_refs": [
        {
          "id": "EVD-execution-87bb2fa37b84412b9a87b15f6b7f0224",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-EXP-PLUS-1001",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-08597008d5464c98a926f6d2e4e9ebf4",
      "evidence_refs": [
        {
          "id": "EVD-execution-08597008d5464c98a926f6d2e4e9ebf4",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-EXP-MINUS-1001",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-457a2565d9044a088e8ec95eea9ca62e",
      "evidence_refs": [
        {
          "id": "EVD-execution-457a2565d9044a088e8ec95eea9ca62e",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-ROWS-100000",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-0a8a0791c8194590bb6890501a62458e",
      "evidence_refs": [
        {
          "id": "EVD-execution-0a8a0791c8194590bb6890501a62458e",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-ROWS-100001",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "BOUNDARY",
      "result": "PASS",
      "execution_id": "execution-bafcde0dd32a489fb8c661d8935d80f4",
      "evidence_refs": [
        {
          "id": "EVD-execution-bafcde0dd32a489fb8c661d8935d80f4",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-INPUT-UNCHANGED-OK",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-003",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "DATA_CONSISTENCY",
      "result": "PASS",
      "execution_id": "execution-d00f94f01fb1497d92271dc40a0f3d98",
      "evidence_refs": [
        {
          "id": "EVD-execution-d00f94f01fb1497d92271dc40a0f3d98",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-INPUT-UNCHANGED-ERROR",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-003",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "DATA_CONSISTENCY",
      "result": "PASS",
      "execution_id": "execution-3a94d563a2ec4718b939c834b16b9e1c",
      "evidence_refs": [
        {
          "id": "EVD-execution-3a94d563a2ec4718b939c834b16b9e1c",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    },
    {
      "case_id": "TC-PLC-UNIT-SUITE",
      "case_version": 1,
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-001",
          "type": "NFR",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "test_type": "FUNCTIONAL",
      "result": "PASS",
      "execution_id": "execution-733005a8f37b49f78611cc28b3df4280",
      "evidence_refs": [
        {
          "id": "EVD-execution-733005a8f37b49f78611cc28b3df4280",
          "type": "EVIDENCE",
          "version": 1
        }
      ]
    }
  ],
  "defects": {
    "total": 0,
    "open": 0,
    "severity": {},
    "items": []
  },
  "traceability": [
    {
      "requirement_id": "REQ-MATRIX-PY-01",
      "version": 1,
      "status": "COMPLETE",
      "missing": []
    },
    {
      "requirement_id": "REQ-MATRIX-PY-02",
      "version": 1,
      "status": "COMPLETE",
      "missing": []
    },
    {
      "requirement_id": "REQ-MATRIX-PY-03",
      "version": 1,
      "status": "COMPLETE",
      "missing": []
    },
    {
      "requirement_id": "REQ-MATRIX-PY-04",
      "version": 1,
      "status": "COMPLETE",
      "missing": []
    },
    {
      "requirement_id": "NFR-MATRIX-PY-001",
      "version": 1,
      "status": "COMPLETE",
      "missing": []
    },
    {
      "requirement_id": "NFR-MATRIX-PY-002",
      "version": 1,
      "status": "COMPLETE",
      "missing": []
    },
    {
      "requirement_id": "NFR-MATRIX-PY-003",
      "version": 1,
      "status": "COMPLETE",
      "missing": []
    }
  ],
  "gates": [
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G0",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G0",
      "ordinal": 0,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G1",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G1",
      "ordinal": 1,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G2",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G2",
      "ordinal": 2,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G3",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G3",
      "ordinal": 3,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G4",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G4",
      "ordinal": 4,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G5",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G5",
      "ordinal": 5,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G6",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G6",
      "ordinal": 6,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G7",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G7",
      "ordinal": 7,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G8",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G8",
      "ordinal": 8,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G9",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G9",
      "ordinal": 9,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G10",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G10",
      "ordinal": 10,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    },
    {
      "current_assessment_id": null,
      "decided_at": null,
      "evaluation_state": "NOT_EVALUATED",
      "gate_id": "G11",
      "gate_status": null,
      "id": "project-337a2843b20e407981e60c2a28c605e4:G11",
      "ordinal": 11,
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "recorded_gate_status": null,
      "freshness": "CURRENT"
    }
  ],
  "conclusion": "PASS",
  "recommend_release": false,
  "release_reasons": [
    "release is absent, changed, failed, rolled back or not ready",
    "G0–G10 release and human acceptance decisions are not all PASS"
  ],
  "execution_records": [
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_json\": true}",
      "case_id": "TC-PLC-UTF8",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:32.968767+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-4bac56f547804c93b8a09043235393c8",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:33.638783+00:00",
      "id": "execution-4bac56f547804c93b8a09043235393c8",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_json\": true}",
      "case_id": "TC-PLC-TOTAL",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:33.668365+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-0ad6ae01f6634090bf184bb021978e60",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:34.331499+00:00",
      "id": "execution-0ad6ae01f6634090bf184bb021978e60",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-001",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_json\": true}",
      "case_id": "TC-PLC-LONG",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:34.362519+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-dda65f9c074c43d4879a177b6ef98485",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:35.189753+00:00",
      "id": "execution-dda65f9c074c43d4879a177b6ef98485",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-001",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_json\": true}",
      "case_id": "TC-PLC-ZERO",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:35.237166+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-446b04cd254241979f2e2e050d3abe36",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:36.223372+00:00",
      "id": "execution-446b04cd254241979f2e2e050d3abe36",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-HEADER-MISSING",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:36.258328+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-ddba8635d4ce47f79af52d40778c7c70",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:37.284244+00:00",
      "id": "execution-ddba8635d4ce47f79af52d40778c7c70",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-HEADER-EXTRA",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:37.329929+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-bf44ead6c482444d9ea45193fefbd12e",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:38.242358+00:00",
      "id": "execution-bf44ead6c482444d9ea45193fefbd12e",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-HEADER-DUPLICATE",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:38.276224+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-16d1bf2e678d4700bb4fb0e339d1f7c1",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:39.195912+00:00",
      "id": "execution-16d1bf2e678d4700bb4fb0e339d1f7c1",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-ROW-MISSING",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:39.233922+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-c56ea2af6d9743abae943067f555bdda",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:40.114840+00:00",
      "id": "execution-c56ea2af6d9743abae943067f555bdda",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-ROW-EXTRA",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:40.148600+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-9c05bfdcecff461cb5dff97fc8601ebc",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:41.089869+00:00",
      "id": "execution-9c05bfdcecff461cb5dff97fc8601ebc",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-ENCODING",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:41.127476+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-7a6e2f2e6cc04231bd4da22348a5cb62",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:42.038483+00:00",
      "id": "execution-7a6e2f2e6cc04231bd4da22348a5cb62",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-EMPTY",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:42.075353+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-98e8a0fef38d4be9bf2e00f7c2b21217",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:43.030651+00:00",
      "id": "execution-98e8a0fef38d4be9bf2e00f7c2b21217",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-HEADER-ONLY",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:43.067491+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-cc28a3acebc141439d456ab85ae6b2f2",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:44.049869+00:00",
      "id": "execution-cc28a3acebc141439d456ab85ae6b2f2",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-DATE-EMPTY",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:44.084046+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-49d6a2e8d74c4c54a10f72ec0b5c29b6",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:44.998879+00:00",
      "id": "execution-49d6a2e8d74c4c54a10f72ec0b5c29b6",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-DATE-FORMAT",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:45.033893+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-1fa83a3f25c14d12b877f810ceb489eb",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:46.011323+00:00",
      "id": "execution-1fa83a3f25c14d12b877f810ceb489eb",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-DATE-CALENDAR",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:46.045542+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-08add237b82e4c2d8e2d00118ec2f855",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:47.051570+00:00",
      "id": "execution-08add237b82e4c2d8e2d00118ec2f855",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-CATEGORY",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:47.088534+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-8f3c514fb8014d40ba9ada89db961a22",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:48.096484+00:00",
      "id": "execution-8f3c514fb8014d40ba9ada89db961a22",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-AMOUNT-EMPTY",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:48.131142+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-d8cd9e1a1b8147d78585fda242128d58",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:49.174868+00:00",
      "id": "execution-d8cd9e1a1b8147d78585fda242128d58",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-AMOUNT-TEXT",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:49.212409+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-2a5587a2450a46b2ba8e9a11018f97b1",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:50.276484+00:00",
      "id": "execution-2a5587a2450a46b2ba8e9a11018f97b1",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-NEGATIVE",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:50.313833+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-da308631e1764b919b059acf0281c1cc",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:51.390062+00:00",
      "id": "execution-da308631e1764b919b059acf0281c1cc",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-NAN",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:51.433014+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-ea25d84b6cf3404cb9938d6de44a1e9f",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:52.483113+00:00",
      "id": "execution-ea25d84b6cf3404cb9938d6de44a1e9f",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-SNAN",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:52.521344+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-69ce1a9e6ba94484867f65461bcd55b6",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:53.605951+00:00",
      "id": "execution-69ce1a9e6ba94484867f65461bcd55b6",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-INFINITY",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:53.643214+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-e5da8cc9584043d8a119ea730130b6d2",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:54.751440+00:00",
      "id": "execution-e5da8cc9584043d8a119ea730130b6d2",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-NEG-INFINITY",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:54.787545+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-d7bcdd8749f4410a8d30c907713ec01b",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:55.926633+00:00",
      "id": "execution-d7bcdd8749f4410a8d30c907713ec01b",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-MISSING-FILE",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:55.965032+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-60a31b2547cc49118cbb2799bf3e3e9b",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:57.029958+00:00",
      "id": "execution-60a31b2547cc49118cbb2799bf3e3e9b",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-NO-ARG",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:57.066530+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-5da7ccb093c7489782c1ba139d5d2610",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:58.209907+00:00",
      "id": "execution-5da7ccb093c7489782c1ba139d5d2610",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-EXTRA-ARG",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:58.244688+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-f41db15aa78045beb3107678eda1cd93",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:28:59.386708+00:00",
      "id": "execution-f41db15aa78045beb3107678eda1cd93",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_decimal\": true, \"exact_category\": true}",
      "case_id": "TC-PLC-DIGITS-1000",
      "case_version": 1,
      "created_at": "2026-09-06T10:28:59.425202+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-4cc30c9d0d314e73b10a2f65a849009a",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:00.620708+00:00",
      "id": "execution-4cc30c9d0d314e73b10a2f65a849009a",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-DIGITS-1001",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:00.658350+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-415cbf55c93a4a88a1c30b9b8463e9bf",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:01.801347+00:00",
      "id": "execution-415cbf55c93a4a88a1c30b9b8463e9bf",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_decimal\": true, \"exact_category\": true}",
      "case_id": "TC-PLC-EXP-PLUS-1000",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:01.834590+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-bfcf1e0e4d7242b0a41c2d1554708f24",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:03.020166+00:00",
      "id": "execution-bfcf1e0e4d7242b0a41c2d1554708f24",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_decimal\": true, \"exact_category\": true}",
      "case_id": "TC-PLC-EXP-MINUS-1000",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:03.055802+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-87bb2fa37b84412b9a87b15f6b7f0224",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:04.229832+00:00",
      "id": "execution-87bb2fa37b84412b9a87b15f6b7f0224",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-EXP-PLUS-1001",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:04.266766+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-08597008d5464c98a926f6d2e4e9ebf4",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:05.499263+00:00",
      "id": "execution-08597008d5464c98a926f6d2e4e9ebf4",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-EXP-MINUS-1001",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:05.538262+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-457a2565d9044a088e8ec95eea9ca62e",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:06.742014+00:00",
      "id": "execution-457a2565d9044a088e8ec95eea9ca62e",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_decimal\": true, \"exact_category\": true}",
      "case_id": "TC-PLC-ROWS-100000",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:06.778535+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-0a8a0791c8194590bb6890501a62458e",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:08.547908+00:00",
      "id": "execution-0a8a0791c8194590bb6890501a62458e",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-ROWS-100001",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:08.588096+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-bafcde0dd32a489fb8c661d8935d80f4",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:10.448126+00:00",
      "id": "execution-bafcde0dd32a489fb8c661d8935d80f4",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"json_strings\": true, \"categories_sorted\": true, \"stderr_empty\": true, \"exact_json\": true}",
      "case_id": "TC-PLC-INPUT-UNCHANGED-OK",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:10.489474+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-d00f94f01fb1497d92271dc40a0f3d98",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:12.728579+00:00",
      "id": "execution-d00f94f01fb1497d92271dc40a0f3d98",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-003",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"stdout_empty\": true, \"stderr_prefix\": true}",
      "case_id": "TC-PLC-INPUT-UNCHANGED-ERROR",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:12.764846+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-3a94d563a2ec4718b939c834b16b9e1c",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:14.097279+00:00",
      "id": "execution-3a94d563a2ec4718b939c834b16b9e1c",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "NFR-MATRIX-PY-003",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    },
    {
      "actual_result": "{\"expected_exit\": true, \"terminated\": true, \"input_unchanged\": true, \"source_unchanged\": true, \"nonzero_test_collection\": true, \"unittest_ok\": true}",
      "case_id": "TC-PLC-UNIT-SUITE",
      "case_version": 1,
      "created_at": "2026-09-06T10:29:14.139228+00:00",
      "environment_ref": {
        "id": "EVD-PLC-ENV",
        "type": "EVIDENCE",
        "version": 1
      },
      "evidence_refs": [
        {
          "id": "EVD-execution-733005a8f37b49f78611cc28b3df4280",
          "type": "EVIDENCE",
          "version": 1
        }
      ],
      "executor_id": "/root/v3_qa_platform",
      "finished_at": "2026-09-06T10:29:16.809982+00:00",
      "id": "execution-733005a8f37b49f78611cc28b3df4280",
      "metrics": {},
      "project_id": "project-337a2843b20e407981e60c2a28c605e4",
      "requirement_refs": [
        {
          "id": "REQ-MATRIX-PY-01",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-02",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-03",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "REQ-MATRIX-PY-04",
          "type": "REQ",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-001",
          "type": "NFR",
          "version": 1
        },
        {
          "id": "NFR-MATRIX-PY-002",
          "type": "NFR",
          "version": 1
        }
      ],
      "result": "PASS",
      "run_id": null,
      "status": "FINISHED",
      "version": 1
    }
  ],
  "source_revision": null,
  "note": "CONDITIONAL PASS is not permission to release; unexecuted types are not coverage claims."
}
```
