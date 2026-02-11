# UI Overhaul Complete - Wizard Navigation

## What Changed

### Before:
- One long scrolling page
- All 5 phases mixed together
- Dense text and tables
- No clear "next step"

### After:
- Clean wizard navigation
- One phase per page
- Clear actions and KPIs
- Always-visible header with storm score

## New Structure

### 1. **Header Bar** (always visible)
- Storm name + tenant
- Storm Play Score (40/100)
- Current phase
- Environment (PROD/STAGE)

### 2. **Sidebar Navigation**
- 📊 Overview
- 🎯 Phase 1: Target
- 📈 Phase 2: Attribution
- 🗺️ Phase 3: Routes
- 🔧 Phase 4: Jobs
- 🔄 Phase 5: Nurture

Plus progress indicators for each phase

### 3. **Phase 3: Routes & Jobs** (Kanban Board)
Four columns:
- **Unassigned**: Routes waiting for crew assignment
- **Assigned**: Routes assigned, ready to start
- **In Progress**: Active routes with completion %
- **Completed**: Finished routes

Each card shows:
- Route name
- ZIP code
- Property count
- Crew assignment
- Progress bar
- Action buttons (Assign/Start/View/Complete)

### 4. **Job Details Drawer**
Click "View Jobs" on any route to see:
- All jobs in that route
- Status for each
- Quick complete button
- Notes and photos (ready to add)

## Files Created

1. **stormops_wizard.py** - Main app with wizard navigation
2. **pages/3_routes.py** - Phase 3 kanban board

## How to Use

### Start the wizard:
```bash
cd /home/forsythe/earth2-forecast-wsl/hotspot_tool
streamlit run stormops_wizard.py
```

### Navigate:
- Use sidebar to jump between phases
- Each phase shows 1-2 primary actions
- Progress bars show completion
- Header always shows context

### Phase 3 Workflow:
1. Generate routes (button)
2. Assign crews (text input + button)
3. Start route (button)
4. View jobs (button)
5. Complete jobs (button per job)
6. Route auto-moves to "Completed"

## What This Fixes

✅ **Guided workflow** - Always know what to do next
✅ **Visual progress** - See completion at a glance
✅ **Actionable tiles** - Every button does something real
✅ **Job board** - Foreman sees routes, crews, and status
✅ **Clean UI** - One focus per page

## Integration with Backend

All buttons connect to existing backend:
- Generate Routes → `RouteBuilder.generate_routes()`
- Assign Crew → Updates `routes` table
- Complete Job → Updates `jobs` table + `policy_outcomes`
- Progress bars → Real data from DB

## Next Steps

The wizard is running at http://localhost:8501

To add more phases:
1. Create `pages/1_target.py`, `pages/2_attribution.py`, etc.
2. Follow same pattern: info box + 1-2 actions + KPIs
3. Wire to existing backend functions

The structure is ready for pilots to use.
