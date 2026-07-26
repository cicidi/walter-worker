from coworker.memory.validate import run_validation, _estimate_tool_calls, _count_incorrect_assumptions, _extract_skill_calls

class TestValidateHelpers:
    def test_estimate_tool_calls(self):
        assert _estimate_tool_calls('no tools') == 0
        assert _estimate_tool_calls('{"tool": "Bash"}') >= 1
    
    def test_count_incorrect(self):
        assert _count_incorrect_assumptions('everything works') == 0
        assert _count_incorrect_assumptions('this is wrong and an error occurred') >= 1
    
    def test_extract_skills(self):
        assert _extract_skill_calls('Skill: test-skill') == ['test-skill']
        assert isinstance(_extract_skill_calls('no skills'), list)

class TestRunValidation:
    def test_basic_run(self):
        report = run_validation('print hello')
        assert 'baseline' in report
        assert 'with_memory' in report
        assert 'verdict' in report
