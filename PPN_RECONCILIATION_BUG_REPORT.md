# PPN Reconciliation Feature - Bug & Issue Report

**Review Date:** 2025-11-06
**Feature:** PPN (Tax) Reconciliation System
**Status:** Implementation Complete, Requires Fixes Before Production

---

## 🔴 CRITICAL ISSUES

### 1. **Missing useEffect Dependency in DataSourceSelector**
**File:** `src/components/ppn/DataSourceSelector.tsx:57-59`

**Issue:**
```typescript
useEffect(() => {
  onDataSelected(selectedSources);
}, [selectedSources]);  // ❌ Missing onDataSelected in dependency array
```

**Impact:**
- React will show ESLint warning about exhaustive deps
- Could cause stale closure issues if `onDataSelected` changes
- May trigger infinite re-renders in some scenarios

**Fix:**
```typescript
useEffect(() => {
  onDataSelected(selectedSources);
}, [selectedSources, onDataSelected]);
```

**Alternative (Better):** Use `useCallback` for `onDataSelected` in parent component

---

### 2. **Missing API Integration in PPNReconciliation Component**
**File:** `src/pages/PPNReconciliation.tsx:21-26`

**Issue:**
```typescript
const handleCreateProject = async (projectData: ProjectFormData) => {
  console.log('Creating project:', projectData);
  // TODO: API call to create project
  // For now, just close the modal
  setIsCreateModalOpen(false);
};
```

**Impact:**
- Projects are NOT actually saved to backend
- Modal closes but project doesn't appear in list
- No persistence - data lost on page refresh
- No error handling for API failures

**Fix Needed:**
```typescript
const handleCreateProject = async (projectData: ProjectFormData) => {
  try {
    const response = await fetch('/api/reconciliation-ppn/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(projectData)
    });

    if (!response.ok) throw new Error('Failed to create project');

    const newProject = await response.json();
    setProjects([newProject, ...projects]);
    setIsCreateModalOpen(false);
    toast.success('Project created successfully!');
  } catch (error) {
    toast.error('Failed to create project');
    throw error; // Re-throw to let modal handle it
  }
};
```

---

### 3. **Missing Project Fetching on Component Mount**
**File:** `src/pages/PPNReconciliation.tsx:17-19`

**Issue:**
```typescript
const [projects] = useState<Project[]>([]);
// ❌ No useEffect to fetch projects from API
```

**Impact:**
- Existing projects are NOT loaded from database
- User always sees "No Projects Yet" even if projects exist
- No way to view/manage existing reconciliation projects

**Fix Needed:**
```typescript
const [projects, setProjects] = useState<Project[]>([]);
const [isLoading, setIsLoading] = useState(true);

useEffect(() => {
  const fetchProjects = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/reconciliation-ppn/projects');
      const data = await response.json();
      setProjects(data);
    } catch (error) {
      toast.error('Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  };

  fetchProjects();
}, []);
```

---

### 4. **No Project Navigation/Detail View**
**File:** `src/pages/PPNReconciliation.tsx:142-178`

**Issue:**
- Project cards have `cursor-pointer` but no onClick handler
- No routing to project detail page
- No way to actually USE a created project

**Impact:**
- Users can create projects but CANNOT open/use them
- Dead-end UX - no path forward after project creation
- Missing entire reconciliation workflow

**Fix Needed:**
1. Create project detail page/route: `/ppn-reconciliation/:projectId`
2. Add onClick handler to navigate:
```typescript
<div
  onClick={() => navigate(`/ppn-reconciliation/${project.id}`)}
  className="border border-gray-200 rounded-lg p-4 hover:border-blue-300..."
>
```

---

## 🟡 HIGH PRIORITY ISSUES

### 5. **Backend Uses In-Memory Storage Instead of Database**
**File:** `backend/routers/reconciliation_ppn.py:117`

**Issue:**
```python
# Temporary in-memory storage for projects
projects_db: Dict[str, Dict[str, Any]] = {}
```

**Impact:**
- All projects lost on server restart
- No data persistence
- Not production-ready
- Multiple server instances will have different data

**Fix Needed:**
- Integrate with actual PostgreSQL database
- Use SQLAlchemy models
- Implement proper CRUD operations with database connection

---

### 6. **Missing Database Models (SQLAlchemy)**
**Files:** Backend missing models for:
- `ppn_projects`
- `ppn_data_sources`
- `ppn_point_a`, `ppn_point_b`, `ppn_point_c`, `ppn_point_e`

**Impact:**
- Cannot run migrations (database tables defined but no ORM models)
- Backend router cannot interact with database properly
- No type safety for database operations

**Fix Needed:**
Create `backend/models/ppn_reconciliation.py`:
```python
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Numeric, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid

class PPNProject(Base):
    __tablename__ = 'ppn_projects'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    # ... rest of fields
```

---

### 7. **Missing Authentication/Authorization**
**File:** `backend/routers/reconciliation_ppn.py`

**Issue:**
- No `get_current_user` dependency in endpoints
- Any user can access/modify any project
- No user_id validation when creating projects

**Impact:**
- Security vulnerability
- Users can see/modify other users' projects
- No access control

**Fix Needed:**
```python
from auth import get_current_user

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user = Depends(get_current_user)  # ✅ Add this
):
    project_data = {
        "user_id": current_user.id,  # ✅ Use authenticated user
        # ... rest
    }
```

---

### 8. **DataSourceSelector Props Interface Mismatch**
**File:** `src/components/ppn/DataSourceSelector.tsx:17-21`

**Issue:**
```typescript
interface DataSourceSelectorProps {
  projectId: string;  // ❌ Declared but not used
  companyNpwp: string;
  onDataSelected: (sources: SelectedDataSources) => void;
}
```

**Impact:**
- Interface declares `projectId` but component doesn't use it
- Misleading API - callers will think they need to provide projectId
- TypeScript confusion

**Fix:**
Either use `projectId` for API calls OR remove from interface:
```typescript
interface DataSourceSelectorProps {
  // projectId: string;  // Remove if not needed
  companyNpwp: string;
  onDataSelected: (sources: SelectedDataSources) => void;
}
```

---

## 🟢 MEDIUM PRIORITY ISSUES

### 9. **Missing Error Boundary for Modal**
**File:** `src/components/ppn/CreateProjectModal.tsx:72-86`

**Issue:**
- If `onSubmit` throws error, modal stays in loading state
- User sees infinite spinner
- No error message displayed to user

**Current Code:**
```typescript
try {
  await onSubmit(formData);
  // Success path
} catch (error) {
  console.error('Failed to create project:', error);  // ❌ Only logs, no UI feedback
} finally {
  setIsSubmitting(false);
}
```

**Fix:**
```typescript
const [submitError, setSubmitError] = useState<string>('');

try {
  await onSubmit(formData);
  setFormData({ ... }); // Reset
  setErrors({});
  setSubmitError('');
  onClose();
} catch (error) {
  setSubmitError(error.message || 'Failed to create project');
  // Don't close modal - let user retry
} finally {
  setIsSubmitting(false);
}

// In JSX, show error:
{submitError && (
  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
    <p className="text-sm text-red-800">{submitError}</p>
  </div>
)}
```

---

### 10. **No Loading State in PPNReconciliation**
**File:** `src/pages/PPNReconciliation.tsx`

**Issue:**
- No loading spinner when fetching projects
- User sees empty state immediately, then projects pop in
- Jarring UX

**Fix:**
```typescript
const [isLoading, setIsLoading] = useState(true);

// In render:
{isLoading ? (
  <div className="flex justify-center items-center py-12">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
  </div>
) : projects.length === 0 ? (
  // Empty state
) : (
  // Projects list
)}
```

---

### 11. **Mock Data in DataSourceSelector**
**File:** `src/components/ppn/DataSourceSelector.tsx:69-94`

**Issue:**
```typescript
// Mock data for now
const mockFiles: ExcelFile[] = [
  { id: '1', filename: 'Faktur_Pajak_Q4_2024.xlsx', ... }
];
```

**Impact:**
- Shows fake data to users
- Cannot select real scanned files
- Non-functional feature

**Fix:**
Replace with real API call:
```typescript
const response = await fetch('/api/reconciliation-excel/files');
const files = await response.json();
```

---

### 12. **Missing Reconciliation Execution Logic**
**File:** `backend/routers/reconciliation_ppn.py:255-290`

**Issue:**
```python
# TODO: Implement actual reconciliation logic
# For now, return mock result
```

**Impact:**
- Reconciliation API endpoint returns dummy data
- No actual matching happens
- Feature is non-functional

**Fix:**
- Integrate `ppn_reconciliation_service.py`
- Load data from selected sources
- Call `run_full_reconciliation()`
- Store results in database

---

### 13. **Missing Point C Count in Project Interface**
**File:** `src/pages/PPNReconciliation.tsx:5-15`

**Issue:**
```typescript
interface Project {
  // ...
  point_a_count?: number;
  point_b_count?: number;
  point_e_count?: number;
  // ❌ Missing point_c_count
}
```

**Impact:**
- Point C count not displayed in UI
- Inconsistent with backend which returns `point_c_count`
- User cannot see Bukti Potong data count

**Fix:**
```typescript
interface Project {
  point_a_count?: number;
  point_b_count?: number;
  point_c_count?: number;  // ✅ Add this
  point_e_count?: number;
}

// In JSX display:
{project.point_c_count && (
  <span>Point C: {project.point_c_count} items</span>
)}
```

---

## 🔵 LOW PRIORITY / NICE-TO-HAVE

### 14. **No Date Validation Against Today**
**File:** `src/components/ppn/CreateProjectModal.tsx:43-47`

**Issue:**
- Only validates end > start
- Doesn't warn if dates are in the future (unusual for tax reconciliation)
- Doesn't validate realistic date ranges

**Suggestion:**
```typescript
const today = new Date();
const oneYearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());

if (new Date(formData.periode_end) > today) {
  newErrors.periode_end = 'End date cannot be in the future';
}
```

---

### 15. **Unused pandas Import**
**File:** `backend/ppn_reconciliation_service.py:6`

**Issue:**
```python
import pandas as pd  # ❌ Never used in the file
```

**Impact:** Minor - just unused import

**Fix:** Remove or use for data processing

---

### 16. **No Pagination for Projects List**
**File:** `src/pages/PPNReconciliation.tsx`

**Issue:**
- Loads ALL projects at once
- Could be slow with hundreds of projects
- No pagination/infinite scroll

**Suggestion:** Add pagination when projects > 20

---

### 17. **No Search/Filter for Projects**
**Issue:** Cannot search projects by name or filter by status/date

**Suggestion:** Add search bar and status filter dropdown

---

### 18. **No Confirmation Dialog for Project Deletion**
**File:** `backend/routers/reconciliation_ppn.py:216-236`

**Issue:**
- DELETE endpoint exists but no UI to call it
- No confirmation prompt

**Suggestion:** Add delete button with confirmation modal

---

### 19. **NPWP Format Not Auto-Formatted**
**File:** `src/components/ppn/CreateProjectModal.tsx:210-220`

**Issue:**
- User must manually type dots/dashes
- No auto-formatting like `01.234.567.8-901.000`

**Suggestion:** Add input formatter to auto-add separators

---

### 20. **Missing Migration Runner Documentation**
**File:** `backend/run_ppn_migration.py`

**Issue:**
- No README explaining how to run migration
- Users won't know they need to run this

**Fix:** Add to main README or create DEPLOYMENT.md

---

## 📊 SUMMARY

### Critical Issues Blocking Production: **4**
1. Missing useEffect dependency
2. No API integration for project creation
3. No project fetching on mount
4. No project navigation/workflow

### High Priority (Data/Security): **4**
5. In-memory storage instead of database
6. Missing SQLAlchemy models
7. No authentication/authorization
8. Props interface mismatch

### Medium Priority (UX/Functionality): **5**
9. No error handling in modal
10. No loading states
11. Mock data in file selector
12. Reconciliation logic not connected
13. Missing Point C count in UI

### Low Priority (Polish): **7**
14-20. Various enhancements

---

## 🚀 RECOMMENDED FIX ORDER

### Phase 1: Make It Work (Critical)
1. Add API integration for projects (create, list, fetch)
2. Add project detail page and navigation
3. Fix useEffect dependencies
4. Add loading states

### Phase 2: Make It Persistent (High)
5. Create SQLAlchemy models
6. Replace in-memory storage with database
7. Add authentication to all endpoints
8. Connect reconciliation execution

### Phase 3: Make It Production-Ready (Medium)
9. Replace mock data with real API calls
10. Add comprehensive error handling
11. Add Point C count to UI
12. Test full workflow end-to-end

### Phase 4: Polish (Low)
13. Add pagination, search, filters
14. Enhance NPWP input formatting
15. Add confirmation dialogs
16. Update documentation

---

## 🎯 NEXT STEPS

1. **Immediate:** Fix API integration in PPNReconciliation component
2. **Next:** Create SQLAlchemy models and connect to database
3. **Then:** Build project detail page with DataSourceSelector
4. **Finally:** Connect reconciliation execution pipeline

**Estimated Time to Production Ready:** 2-3 days of focused development
