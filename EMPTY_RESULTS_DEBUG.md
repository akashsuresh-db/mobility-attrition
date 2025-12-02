# 🔍 Debugging Empty Genie Results

## Problem
OBO is working (no more 403 errors), but Genie returns empty results when asked to show data.

---

## Possible Causes

### 1. **RLS Filtering All Rows (Most Likely)** ⚠️

**Symptom:** Genie query executes successfully but returns 0 rows

**Cause:** Unity Catalog RLS is working as designed - filtering out all rows for your user

**Check:**
1. What department/BU is your user (`akash.s@databricks.com`) assigned to in the RLS rules?
2. Does the question ask for "all BUs" but RLS only allows you to see YOUR BU?

**Example:**
```
Question: "Show me average attrition across ALL BUs"
RLS Rule: User can only see HR department
Result: Query runs, but returns 0 rows because:
  - ALL BUs includes: Sales, Engineering, Marketing, HR
  - Your RLS allows: HR only
  - Genie tries to aggregate across ALL → Gets empty result
```

**Fix:** 
- Ask for data within YOUR scope: "Show me average attrition in MY department"
- OR: Admin needs to grant you access to more departments

---

### 2. **Genie Query Failed Silently**

**Symptom:** No error message, just empty response

**Check Agent Logs:**
Look for these DEBUG lines in the serving endpoint logs:

```
DEBUG Genie - Response type: <class 'dict'>
DEBUG Genie - Response keys: ...
DEBUG Genie - Found 'output' field: ...
DEBUG - Genie response length: ...
DEBUG - Genie response preview: ...
```

**If you see:**
```
DEBUG - Genie response length: 0
```
→ Genie returned nothing (query failed or returned empty)

---

### 3. **RLS Row-Level Filter vs Aggregation Issue**

**The Problem:**
When you ask for "average across ALL BUs" but RLS only allows ONE BU:

**What Happens:**
```sql
-- Genie generates (conceptually):
SELECT BU, AVG(attrition_rate)
FROM employees
WHERE <RLS filter: BU = 'HR'>  -- Applied by Unity Catalog
GROUP BY BU

-- Result: Only HR data
-- But question asked for "ALL BUs"
-- Genie sees mismatch → Returns empty/error
```

**Solution:**
Ask questions that match your RLS scope:
- ✅ "Show me attrition rate in my department"
- ✅ "What's the average attrition for employees I can see?"
- ❌ "Show me ALL departments" (if RLS limits you to one)

---

## 🔍 How to Diagnose

### Step 1: Check Agent Endpoint Logs

**In Databricks UI:**
```
1. Go to Serving → Endpoints
2. Find: agents_akash_s_demo-talent-talent_agent_v1
3. Click "Logs" tab
4. Filter to your recent request
5. Look for DEBUG lines from Genie
```

**What to look for:**
```
DEBUG Genie - Response type: dict
DEBUG Genie - Found 'output' field: [WHAT IS HERE?]
DEBUG - Genie response length: [IS THIS 0?]
DEBUG - Genie response preview: [WHAT DOES THIS SAY?]
```

---

### Step 2: Test Genie Directly

**Test in Genie Space UI:**
1. Go to your Genie Space
2. Ask the SAME question: "show me average employee attrition across all the BUs"
3. Does it return data?
   - **YES** → Problem is in agent code
   - **NO** → Problem is RLS or data access

---

### Step 3: Test with RLS-Scoped Question

**Try asking:**
```
"Show me the attrition rate for the HR department"
```

**If this works but "all BUs" doesn't:**
→ Confirms RLS is working, just filtering your "all BUs" query

---

### Step 4: Check RLS Configuration

**In Unity Catalog:**
1. Go to the table (e.g., `akash_s_demo.talent.fact_attrition_snapshots`)
2. Check Row Filters
3. What filter applies to user `akash.s@databricks.com`?

**Expected:**
```sql
-- Example RLS rule
WHERE department = current_user_department()
-- or
WHERE department = 'HR' AND user_email = 'akash.s@databricks.com'
```

---

## 🔧 Fixes Based on Diagnosis

### Fix 1: Adjust Question to Match RLS Scope

**If RLS limits you to HR department:**

**Instead of:**
```
"Show me average attrition across ALL BUs"
```

**Ask:**
```
"Show me the attrition rate for my department"
"What's the attrition rate for employees I have access to?"
"Show me attrition data for the HR team"
```

---

### Fix 2: If Genie Returns Empty But Should Have Data

**Check if this is a Genie aggregation issue:**

Some Genie queries fail when:
- Asking for aggregation across all groups
- But RLS filters to only one group
- Genie can't reconcile the mismatch

**Workaround:**
Be more specific in your question to match your data scope.

---

### Fix 3: If You Need Access to All BUs

**Admin must:**
1. Update RLS rules to grant you access to all departments
2. OR remove RLS (not recommended for production)

---

## 📊 Expected Agent Logs (Working Case)

**When Genie returns data:**
```
DEBUG Genie - Input messages: 1
DEBUG Genie - Response type: <class 'dict'>
DEBUG Genie - Found 'output' field: | Department | Attrition Rate |
                                      | HR | 18.5% |
DEBUG Genie - Created AIMessage with content length: 156
DEBUG - Messages count: 3
DEBUG - Genie response length: 156
DEBUG - Genie response preview: | Department | Attrition Rate |
                                  |------------|----------------|
                                  | HR         | 18.5%          |
DEBUG - Cleaned genie response length: 142
DEBUG Supervisor - Final response length: 245
```

**When Genie returns empty (RLS filtered all rows):**
```
DEBUG Genie - Input messages: 1
DEBUG Genie - Response type: <class 'dict'>
DEBUG Genie - Found 'output' field: Query executed but returned no rows
DEBUG Genie - Created AIMessage with content length: 45
DEBUG - Messages count: 3
DEBUG - Genie response length: 45
DEBUG - Genie response preview: Query executed but returned no rows
ERROR: {error_msg}
```

---

## 🎯 Quick Test Questions

### Test 1: Scoped to Your Department
```
"What's the attrition rate in the HR department?"
```
**Expected:** Should return data (if you have HR access)

### Test 2: Your User's Data
```
"Show me employee data I have access to"
```
**Expected:** Should return your RLS-filtered data

### Test 3: Specific Metric
```
"How many employees are in my department?"
```
**Expected:** Count of employees in your RLS scope

### Test 4: Broad Question (May Fail)
```
"Show me ALL departments' attrition rates"
```
**Expected:** May return empty if RLS limits you to one department

---

## 🚨 Common Pitfall

**The "All BUs" Trap:**

When RLS is enabled and limits you to ONE department:
- ❌ "Show me all BUs" → Returns empty (no access to "all")
- ✅ "Show me my BU" → Returns HR data (your scope)

**This is RLS working correctly!** The agent is using YOUR credentials, so you only see YOUR data.

**To test RLS is working:**
- User A (HR) should only see HR data
- User B (Engineering) should only see Engineering data
- Neither should see "all departments"

---

## 📋 Diagnostic Checklist

- [ ] Check agent endpoint logs for DEBUG lines
- [ ] Look at "Genie response length" - is it 0?
- [ ] Test same question directly in Genie Space UI
- [ ] Does Genie UI return data? (YES/NO)
- [ ] Try RLS-scoped question like "my department"
- [ ] Does scoped question work? (YES/NO)
- [ ] Check Unity Catalog RLS rules for your user
- [ ] What department/BU does RLS allow you to see?
- [ ] Does your question match your RLS scope?

---

## ✅ Next Steps

1. **Share agent endpoint logs** from your "all BUs" query
2. **Test in Genie UI** with same question
3. **Try scoped question** like "my department"
4. **Check RLS rules** to understand your data scope

Then we can identify if it's:
- RLS working as designed (need to ask scoped questions)
- Genie query issue (need to fix agent code)
- Data access issue (need admin to grant permissions)

---

**Most Likely:** RLS is working perfectly - you're just asking for data outside your scope! Try a scoped question and see if that works.

