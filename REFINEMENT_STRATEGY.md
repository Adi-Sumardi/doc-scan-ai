# 🎯 NEW HYBRID REFINEMENT STRATEGY

## Problem Statement
Current system has 2 modes:
1. **Bank Adapter Success** → Use adapter result ✅
2. **Bank Adapter Fail** → Fallback to FULL GPT-4o ❌ (expensive!)

## Proposed Solution: ALWAYS REFINE Strategy

```
PDF → Google Document AI → JSON
                             ↓
                    Bank Adapter (Extract)
                    - Always runs first
                    - Extract what it can (even partial!)
                    - Mark confidence per field
                             ↓
                    GPT-4o Refinement (ALWAYS)
                    - Input: Bank adapter result
                    - Task: Fill missing fields ONLY
                    - Validate & clean data
                    - Much cheaper (refinement vs full extract)
                             ↓
                    Perfect Result ✨
```

## Token Usage Comparison

### Current Strategy:
**Scenario 1: Adapter Success (90% cases)**
- Bank Adapter: 0 tokens (free) ✅
- GPT: 0 tokens (not called) ✅
- **Total: 0 tokens**

**Scenario 2: Adapter Fail (10% cases)**
- Bank Adapter: 0 tokens (but failed)
- GPT Full Extract: 15,000 input + 2,000 output = 17,000 tokens ❌
- **Total: 17,000 tokens**

**Average: (90% × 0) + (10% × 17,000) = 1,700 tokens per file**

### New Refinement Strategy:
**All cases (100%)**
- Bank Adapter: 0 tokens (always runs) ✅
- GPT Refinement: 500 input + 300 output = 800 tokens ✅
- **Total: 800 tokens per file**

**Savings vs current:**
- When adapter succeeds: +800 tokens (small increase)
- When adapter fails: 17,000 → 800 = **16,200 tokens saved!**
- **Average: 1,700 → 800 = 53% reduction**

**Cost per file:**
- Current: ~$0.03-0.05
- New: ~$0.01-0.02
- **Savings: 50-60%**

## Benefits

### 1. Cost Efficiency
- 50-60% token reduction on average
- Especially beneficial when adapters partially work

### 2. Quality Improvement
- GPT validates ALL results (even adapter successes)
- Catches adapter errors
- Fills missing fields
- Standardizes format

### 3. Consistency
- EVERY file goes through same refinement
- No "adapter worked OR GPT worked" dichotomy
- Predictable results

### 4. Better Handling of Partial Success
**Current**: Adapter gets 80% → marked as "fail" → full GPT
**New**: Adapter gets 80% → GPT fills 20% → perfect!

## Implementation

### Step 1: Always Run Bank Adapter
```python
# Rule-based parsing (always runs, no matter what)
adapter_result = bank_adapter.extract(ocr_json)

# Even if adapter returns 0 transactions, we still pass to GPT
# GPT will have bank_name, account_number, etc. from adapter
```

### Step 2: GPT Refinement (Always)
```python
refinement_prompt = f"""
You are refining bank statement data extracted by a rule-based parser.

ADAPTER EXTRACTED:
- Bank: {adapter_result['bank_name']}
- Account: {adapter_result['account_number']}
- Transactions: {len(adapter_result['transactions'])} found
- Saldo Awal: {adapter_result['saldo_awal']}

ADAPTER RESULT:
{json.dumps(adapter_result, indent=2)}

YOUR TASK:
1. Validate all extracted data
2. Fill ANY missing fields you can find in the OCR
3. Fix any obvious errors
4. Return COMPLETE result

Only include corrections/additions, don't re-output correct data.

FORMAT:
{{
  "corrections": [...],
  "missing_transactions": [...],
  "field_updates": {{...}}
}}
"""

# Much smaller prompt = fewer tokens!
gpt_refinement = await gpt4o(refinement_prompt)
final_result = merge(adapter_result, gpt_refinement)
```

### Step 3: Merge Strategy
```python
def merge_adapter_with_refinement(adapter_result, gpt_refinement):
    """Merge adapter result with GPT refinements"""

    # Start with adapter result
    final = adapter_result.copy()

    # Apply GPT corrections
    for correction in gpt_refinement['corrections']:
        final['transactions'][correction['index']] = correction['corrected']

    # Add missing transactions
    final['transactions'].extend(gpt_refinement['missing_transactions'])

    # Update fields
    final.update(gpt_refinement['field_updates'])

    # Sort by date
    final['transactions'].sort(key=lambda x: x['tanggal'])

    return final
```

## Metrics to Track

```python
{
    "adapter_transactions": 45,  # What adapter found
    "gpt_added_transactions": 5,  # What GPT added
    "gpt_corrections": 2,          # What GPT fixed
    "final_transactions": 50,      # Total
    "adapter_accuracy": 90%,       # 45/50
    "token_usage": 800,
    "cost": $0.012
}
```

## Rollout Plan

### Phase 1: Parallel Testing (Week 1)
- Run both strategies in parallel
- Compare results
- Measure token usage
- Validate accuracy

### Phase 2: Gradual Rollout (Week 2)
- Enable for 10% of traffic
- Monitor metrics
- Adjust prompts if needed

### Phase 3: Full Deployment (Week 3)
- Roll out to 100%
- Remove old fallback code
- Optimize refinement prompts

## Expected Results

### Quality Metrics
- **Accuracy**: 95% → 98% (GPT validates everything)
- **Completeness**: 85% → 99% (GPT fills gaps)
- **Consistency**: Variable → High (same path for all)

### Cost Metrics
- **Token usage**: -50-60% average
- **API calls**: Same (1 GPT call per file)
- **Processing time**: +2-3s (minimal increase)
- **Monthly cost**: $500 → $250 (estimated)

### Reliability Metrics
- **Adapter failures**: No longer critical
- **Partial successes**: Now useful
- **Edge cases**: Better handled

## Conclusion

The "Always Refine" strategy combines the best of both worlds:
- ✅ Speed & cost efficiency of bank adapters
- ✅ Flexibility & accuracy of GPT
- ✅ Consistent quality across all files
- ✅ 50-60% token savings
- ✅ Better handling of edge cases

**Recommendation: IMPLEMENT IMMEDIATELY**
