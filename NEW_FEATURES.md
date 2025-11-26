# PrimeTime - New Features Documentation

**Date:** November 13, 2025
**Version:** 1.1.0

---

## 🎯 Overview

This document describes the powerful new features added to PrimeTime to enhance supervisor-student interactions, progress tracking, and event submission workflows with approval mechanisms.

---

## ✨ New Features

### 1. Supervisor Feedback & Log Sheet System 📝

**Purpose:** Enable supervisors to provide structured feedback to their students with sentiment analysis and action tracking.

#### Model: `SupervisorFeedback`

**Location:** `analytics/models.py`

**Key Features:**
- ✅ Date-based feedback entries
- ✅ Context and detailed remarks
- ✅ **Automatic sentiment analysis** of feedback
- ✅ 5-point rating system
- ✅ Action tracking (requires immediate action?)
- ✅ Follow-up tracking with dates
- ✅ Visibility control (show/hide from students)
- ✅ Integration with progress and stress calculations

#### Fields:

| Field | Type | Description |
|-------|------|-------------|
| student | ForeignKey | Student receiving feedback |
| supervisor | ForeignKey | Supervisor giving feedback |
| project | ForeignKey | Related project |
| date | DateField | Feedback date |
| context | CharField | Brief context (200 chars) |
| remarks | TextField | Detailed feedback |
| sentiment_score | FloatField | Auto-calculated sentiment (-1 to 1) |
| rating | IntegerField | Performance rating (1-5) |
| action_required | BooleanField | Needs immediate action? |
| follow_up_required | BooleanField | Needs follow-up? |
| follow_up_date | DateField | When to follow up |
| is_visible_to_student | BooleanField | Student can see? |

#### Usage Example:

```python
from analytics.models import SupervisorFeedback

# Create feedback
feedback = SupervisorFeedback.objects.create(
    student=student_user,
    supervisor=supervisor_user,
    project=project,
    date=timezone.now().date(),
    context="Weekly progress review",
    remarks="Excellent work on the frontend. However, backend API integration needs more attention. Please focus on completing the authentication module by next week.",
    rating=4,
    action_required=True,
    follow_up_required=True,
    follow_up_date=timezone.now().date() + timedelta(days=7)
)

# Calculate sentiment automatically
feedback.calculate_sentiment()
# sentiment_score will be ~0.2 (slightly positive)
# sentiment_category will be "Neutral"
```

#### Admin Features:
- ✅ Visual rating display with stars (⭐⭐⭐⭐)
- ✅ Sentiment badges (😊 Positive, 😐 Neutral, 😞 Negative)
- ✅ Action required indicators
- ✅ Bulk actions: Calculate sentiment, Show/Hide from students
- ✅ Date hierarchy navigation
- ✅ Advanced filtering

---

### 2. Enhanced Analytics Integration 📊

#### How Feedback Affects Progress:

The `SupervisorFeedback` model integrates with the existing analytics system:

**Stress Calculation:**
- Negative feedback sentiment increases stress levels
- Action-required feedback adds stress
- Low ratings increase stress

**Progress Calculation:**
- Positive feedback sentiment boosts progress score
- High ratings improve progress metrics
- Regular feedback sessions indicate active engagement

#### Enhanced `ProgressCalculator`:

The calculator now considers:
1. **Deliverables:** 50% weight
2. **Marks:** 30% weight
3. **Activity:** 20% weight
4. **Supervisor Feedback Sentiment:** Modifier (+/-5%)

#### Enhanced `StressCalculator`:

The calculator now includes:
1. **Workload:** 25% weight
2. **Deadlines:** 35% weight
3. **Social Isolation:** 15% weight
4. **Feedback Sentiment:** 25% weight (NEW!)

---

### 3. Event Submission System with Approval Workflow 📤

**Purpose:** Allow admins to create deadline events requiring file submissions that go through a two-stage approval process (Supervisor → Admin).

#### Model: `EventSubmission`

**Location:** `events/models.py`

**Workflow:**
```
Student Submits
    ↓
[Pending] → Supervisor Review
    ↓
Supervisor Approves/Rejects
    ↓
[Supervisor Approved] → Admin Review
    ↓
Admin Approves/Rejects
    ↓
[Final Status] → Affects Grades
```

#### Key Features:
- ✅ Multi-stage approval (Supervisor → Admin)
- ✅ File upload support (PDF, DOCX, PPTX, etc.)
- ✅ Late submission detection and penalties
- ✅ Version tracking for resubmissions
- ✅ Supervisor and admin ratings (1-5)
- ✅ Detailed remarks at each stage
- ✅ Grade impact calculation
- ✅ **Automatic grade reduction if supervisor doesn't approve before deadline**

#### Submission Status Flow:

| Status | Description | Next Action |
|--------|-------------|-------------|
| `pending` | Just submitted | Supervisor reviews |
| `supervisor_review` | Under supervisor review | Supervisor approves/rejects |
| `supervisor_approved` | Supervisor approved | Moves to admin |
| `supervisor_rejected` | Supervisor rejected | Student can resubmit |
| `admin_review` | Under admin review | Admin approves/rejects |
| `admin_approved` | **FINAL APPROVAL** | Grade recorded |
| `admin_rejected` | **FINAL REJECTION** | Grade penalized |
| `resubmitted` | Student resubmitted | Supervisor reviews v2 |

#### Fields:

| Field | Type | Description |
|-------|------|-------------|
| event | ForeignKey | Related deadline event |
| student | ForeignKey | Student submitting |
| submission_file | FileField | Uploaded file |
| file_type | CharField | File type (pdf, docx, pptx) |
| submission_notes | TextField | Student's notes |
| status | CharField | Current status |
| version | IntegerField | Submission version (for resubmissions) |
| late_submission | BooleanField | Was it late? |
| late_penalty | FloatField | Penalty amount |
| supervisor_reviewed_at | DateTimeField | When supervisor reviewed |
| supervisor_remarks | TextField | Supervisor's feedback |
| supervisor_rating | IntegerField | Supervisor's rating (1-5) |
| admin_reviewed_at | DateTimeField | When admin reviewed |
| admin_remarks | TextField | Admin's feedback |
| admin_rating | IntegerField | Admin's rating (1-5) |
| grade_impact | FloatField | Impact on overall grade |

#### Usage Example:

```python
from events.models import Event, EventSubmission

# Admin creates deadline event
event = Event.objects.create(
    title="Project Proposal Submission",
    event_type='deadline',
    start_datetime=timezone.now(),
    end_datetime=timezone.now() + timedelta(days=7),
    description="Submit your project proposal document",
    requires_submission=True,
    submission_file_type="PDF",
    submission_instructions="Submit a 5-10 page proposal with: Introduction, Objectives, Methodology, Timeline, References",
    late_submission_penalty=10.0,  # 10% penalty
    organizer=admin_user,
    batch_year=2025
)

# Student submits
submission = EventSubmission.objects.create(
    event=event,
    student=student_user,
    submission_file=uploaded_file,
    file_type='pdf',
    submission_notes="Please review my project proposal for the AI-powered chatbot."
)

# Check if late
if submission.is_late():
    submission.late_submission = True
    submission.late_penalty = event.late_submission_penalty
    submission.save()

# Supervisor reviews and approves
submission.supervisor_approve(
    remarks="Good proposal structure. Clear objectives and realistic timeline.",
    rating=4
)
# Status automatically changes to 'admin_review'

# Admin gives final approval
submission.admin_approve(
    remarks="Well-structured proposal. Approved for implementation phase.",
    rating=5
)
# Status changes to 'admin_approved'
# Grade impact is recorded

# If student needs to resubmit
if submission.status == 'supervisor_rejected':
    new_submission = submission.resubmit(
        new_file=revised_file,
        notes="Revised based on feedback - added more details to methodology"
    )
    # Creates version 2
```

---

### 4. Enhanced Event Model 📅

**New Fields Added to `Event` model:**

| Field | Type | Description |
|-------|------|-------------|
| requires_submission | BooleanField | Does event require submission? |
| submission_file_type | CharField | Expected file type |
| submission_instructions | TextField | Instructions for students |
| late_submission_penalty | FloatField | Penalty for late submission (%) |
| max_file_size_mb | IntegerField | Maximum file size allowed |

---

## 🎯 User Workflows

### Supervisor Workflow

#### 1. **Viewing Student Profile**

When a supervisor opens their assigned student's profile, they see:

```
┌─────────────────────────────────────────┐
│ Student: Alice Johnson                   │
│ Project: AI-Powered Learning System      │
├─────────────────────────────────────────┤
│ Current Stress Level: 65% (High)        │
│ Project Progress: 73%                    │
│ Last Meeting: Nov 10, 2025              │
├─────────────────────────────────────────┤
│ 📝 LOG SHEET                            │
│                                          │
│ [+ Add New Feedback]                     │
│                                          │
│ Nov 12, 2025 - Weekly Review            │
│ Rating: ⭐⭐⭐⭐                         │
│ Sentiment: 😊 Positive                  │
│ "Great progress on frontend..."         │
│                                          │
│ Nov 5, 2025 - Technical Discussion      │
│ Rating: ⭐⭐⭐                           │
│ Sentiment: 😐 Neutral                   │
│ "Need to improve API integration..."     │
└─────────────────────────────────────────┘
```

#### 2. **Providing Feedback**

Supervisors can:
- Enter date, context, and detailed remarks
- Rate performance (1-5 stars)
- Mark if action is required
- Set follow-up dates
- Choose visibility (show/hide from student)

**Automatic Features:**
- Sentiment is calculated automatically from remarks
- Feedback affects student's progress and stress metrics
- Student receives notification (if visible)

#### 3. **Reviewing Submissions**

When students submit files for deadline events:

```
┌─────────────────────────────────────────┐
│ PENDING REVIEWS                          │
├─────────────────────────────────────────┤
│ Alice Johnson - Proposal Submission      │
│ Submitted: Nov 13, 2025 (On Time)       │
│ File: proposal_v1.pdf                    │
│ Notes: "Please review my proposal"       │
│                                          │
│ [View File] [Approve] [Reject]          │
└─────────────────────────────────────────┘
```

**Review Actions:**
1. **Approve** → Moves to admin for final approval
2. **Reject** → Student can resubmit with improvements

**Supervisor provides:**
- Detailed remarks
- Rating (1-5)
- Decision (approve/reject)

---

### Student Workflow

#### 1. **Viewing Feedback**

Students see their supervisor's feedback on their profile:

```
┌─────────────────────────────────────────┐
│ MY FEEDBACK HISTORY                      │
├─────────────────────────────────────────┤
│ Nov 12, 2025                             │
│ Context: Weekly Progress Review          │
│ Rating: ⭐⭐⭐⭐                         │
│                                          │
│ "Excellent work on the frontend. The UI │
│  is intuitive and responsive. However,   │
│  backend API integration needs more      │
│  attention. Focus on authentication."    │
│                                          │
│ ⚠️ Action Required                      │
│ Follow-up: Nov 19, 2025                  │
└─────────────────────────────────────────┘
```

#### 2. **Submitting to Deadlines**

When a deadline event exists:

```
┌─────────────────────────────────────────┐
│ EVENT: Project Proposal Submission       │
│ Deadline: Nov 20, 2025, 11:59 PM        │
├─────────────────────────────────────────┤
│ Required: PDF document                   │
│ Max Size: 10 MB                          │
│                                          │
│ Instructions:                            │
│ Submit a 5-10 page proposal with:        │
│ - Introduction                           │
│ - Objectives                             │
│ - Methodology                            │
│ - Timeline                               │
│ - References                             │
│                                          │
│ [Choose File] [Upload & Submit]          │
└─────────────────────────────────────────┘
```

**After Submission:**

Student tracks progress:

```
┌─────────────────────────────────────────┐
│ SUBMISSION STATUS                        │
├─────────────────────────────────────────┤
│ Version: 1                               │
│ Status: ⏳ Under Supervisor Review       │
│ Submitted: Nov 13, 2025 (On Time)       │
│                                          │
│ Timeline:                                │
│ ✅ Submitted by Student                 │
│ ⏳ Pending Supervisor Review             │
│ ⬜ Pending Admin Review                  │
│ ⬜ Final Approval                        │
└─────────────────────────────────────────┘
```

**If Rejected:**

```
┌─────────────────────────────────────────┐
│ ❌ SUBMISSION REJECTED                   │
├─────────────────────────────────────────┤
│ Supervisor Remarks:                      │
│ "Proposal needs more detail in the       │
│  methodology section. Also add more      │
│  references (at least 10)."              │
│                                          │
│ Rating: ⭐⭐                             │
│                                          │
│ [Resubmit] (Upload revised version)      │
└─────────────────────────────────────────┘
```

---

### Admin Workflow

#### 1. **Viewing All Log Sheets**

Admins see system-wide feedback overview:

```
┌─────────────────────────────────────────┐
│ ALL STUDENT FEEDBACK (System-wide)       │
├─────────────────────────────────────────┤
│ Filter: [Batch: 2025] [Dept: CS]        │
│ Sort: [Latest First]                     │
│                                          │
│ Alice Johnson (CS) - Dr. Smith           │
│ Latest: Nov 12 | Rating: ⭐⭐⭐⭐        │
│ Stress: 65% (High) | Progress: 73%      │
│ ⚠️ 2 Action-Required Items              │
│                                          │
│ Bob Wilson (CS) - Dr. Jones              │
│ Latest: Nov 10 | Rating: ⭐⭐⭐          │
│ Stress: 45% (Moderate) | Progress: 82%  │
│ ✅ No Actions Required                  │
└─────────────────────────────────────────┘
```

#### 2. **Final Approval of Submissions**

After supervisor approval, admin reviews:

```
┌─────────────────────────────────────────┐
│ SUBMISSIONS AWAITING FINAL APPROVAL      │
├─────────────────────────────────────────┤
│ Alice Johnson - Project Proposal         │
│ Version: 1                               │
│                                          │
│ ✅ Supervisor Approved                  │
│    Rating: ⭐⭐⭐⭐                      │
│    "Good structure and clear objectives" │
│                                          │
│ [View File] [Final Approve] [Reject]    │
│                                          │
│ If not approved by deadline (Nov 20):    │
│ ⚠️ Grade penalty: -10%                  │
└─────────────────────────────────────────┘
```

---

## 🔄 Integration with Existing Features

### Progress Calculation

**Old Formula:**
```
Progress = (Deliverables × 50%) + (Marks × 30%) + (Activity × 20%)
```

**New Formula:**
```
Progress = (Deliverables × 50%) + (Marks × 30%) + (Activity × 20%)
           × FeedbackModifier

FeedbackModifier = 1 + (AvgSentiment × 0.05)
```

**Example:**
- Deliverables: 80%
- Marks: 75%
- Activity: 90%
- Avg Feedback Sentiment: +0.4 (positive)

```
Base Progress = (80×0.5) + (75×0.3) + (90×0.2) = 80.5%
Modifier = 1 + (0.4 × 0.05) = 1.02
Final Progress = 80.5% × 1.02 = 82.1%
```

### Stress Calculation

**New Component:**
- **Feedback Sentiment:** 25% weight
- Negative feedback increases stress
- Positive feedback decreases stress

**Example:**
```
Workload Stress: 60%
Deadline Stress: 70%
Social Stress: 40%
Feedback Avg Sentiment: -0.3 (negative)

Feedback Stress = (1 - ((-0.3 + 1) / 2)) × 100 = 65%

Total Stress = (60×0.25) + (70×0.35) + (40×0.15) + (65×0.25)
             = 15 + 24.5 + 6 + 16.25
             = 61.75% (High)
```

---

## 📊 Admin Panel Features

### SupervisorFeedback Admin

**List View:**
- Student name
- Supervisor name
- Date
- Rating with stars (⭐⭐⭐⭐)
- Sentiment badge (😊/😐/😞)
- Action required indicator
- Visibility status

**Actions:**
- Calculate sentiment for selected
- Make visible to students
- Hide from students

**Filters:**
- Date range
- Rating (1-5)
- Action required
- Visible to student
- Follow-up required

### EventSubmission Admin

**List View:**
- Student name
- Event title
- Version number
- Status badge (colored)
- Submission date
- Late/On-time indicator
- Supervisor rating
- Admin rating
- Final approval status

**Actions:**
- Approve as Supervisor (bulk)
- Reject as Supervisor (bulk)
- Final Approval (Admin bulk)
- Final Rejection (Admin bulk)

**Filters:**
- Status
- Submission date
- Late submission
- Version

---

## 🎓 Grade Impact System

### How Grades are Affected

#### Scenario 1: On-Time, Approved
```
Base Grade: 100%
Late Penalty: 0%
Supervisor Rating: 4/5 → +5%
Admin Rating: 5/5 → +5%
═══════════════════════════
Final Grade: 110% (capped at 100%)
```

#### Scenario 2: Late, Eventually Approved
```
Base Grade: 100%
Late Penalty: -10%
Supervisor Rating: 3/5 → 0%
Admin Rating: 4/5 → +5%
═══════════════════════════
Final Grade: 95%
```

#### Scenario 3: On-Time, but Rejected
```
Base Grade: 100%
Late Penalty: 0%
Supervisor Rejected: -20%
Resubmitted & Approved: Partial recovery (+10%)
═══════════════════════════
Final Grade: 90%
```

#### Scenario 4: Late & Supervisor Never Approves Before Deadline
```
Base Grade: 100%
Late Penalty: -10%
No Supervisor Approval: -25%
═══════════════════════════
Final Grade: 65% (FAILED)
```

---

## 💡 Best Practices

### For Supervisors

1. **Provide Regular Feedback**
   - Weekly or bi-weekly log sheet entries
   - Balance positive and constructive feedback
   - Be specific in remarks

2. **Use Ratings Consistently**
   - 5: Excellent, exceeded expectations
   - 4: Above expectations
   - 3: Meets expectations
   - 2: Below expectations
   - 1: Needs significant improvement

3. **Review Submissions Promptly**
   - Review within 48 hours of submission
   - Provide detailed remarks for rejections
   - Approve quickly if requirements are met

4. **Set Clear Follow-ups**
   - Use follow-up dates for action items
   - Mark critical issues as "action required"
   - Track follow-up completion

### For Students

1. **Submit Early**
   - Don't wait until the deadline
   - Leave time for potential resubmissions
   - Check submission requirements carefully

2. **Review Feedback Regularly**
   - Check feedback weekly
   - Act on action-required items immediately
   - Ask for clarification if needed

3. **Resubmit Properly**
   - Address all points in rejection remarks
   - Add notes explaining changes made
   - Submit well before deadline

### For Admins

1. **Create Clear Deadlines**
   - Provide detailed instructions
   - Specify file types and size limits
   - Set reasonable late penalties

2. **Monitor Approval Workflow**
   - Check for stuck submissions
   - Remind supervisors to review
   - Provide final approval promptly

3. **Review System-Wide Patterns**
   - Monitor stress levels across students
   - Identify struggling students early
   - Facilitate supervisor-student communication

---

## 🔧 Technical Implementation

### Database Migrations

```bash
# Apply new migrations
python manage.py migrate analytics
python manage.py migrate events

# Verify migrations
python manage.py showmigrations analytics
python manage.py showmigrations events
```

### Admin Registration

All new models are automatically registered:
- `SupervisorFeedback` in `analytics/admin.py`
- `EventSubmission` in `events/admin.py`

### Access Permissions

**SupervisorFeedback:**
- Supervisors: Create, Read, Update (own feedback only)
- Students: Read (if visible_to_student=True)
- Admins: Full access

**EventSubmission:**
- Students: Create, Read (own submissions)
- Supervisors: Read, Update (review/approve/reject)
- Admins: Full access (final approval)

---

## 📈 Metrics & Analytics

### New Dashboard Widgets

**Supervisor Dashboard:**
- Students requiring attention (action-required feedback)
- Pending submission reviews
- Average feedback sentiment
- Student stress levels

**Student Dashboard:**
- Recent feedback summary
- Pending submissions
- Upcoming deadlines
- Grade impact tracking

**Admin Dashboard:**
- System-wide feedback overview
- Submission approval pipeline
- At-risk students (high stress, low progress)
- Supervisor activity metrics

---

## 🚀 Quick Start Examples

### Example 1: Supervisor Gives Feedback

```python
# In supervisor view/form
feedback = SupervisorFeedback.objects.create(
    student=student,
    supervisor=request.user,
    project=student.projects.first(),
    date=timezone.now().date(),
    context="Mid-project review",
    remarks="Strong progress on core features. Database design is solid. Need to improve error handling and add more unit tests.",
    rating=4,
    action_required=True,
    is_visible_to_student=True
)
feedback.calculate_sentiment()  # Auto-calculates
```

### Example 2: Student Submits to Deadline

```python
# In student submission view
submission = EventSubmission.objects.create(
    event=deadline_event,
    student=request.user,
    submission_file=request.FILES['file'],
    file_type='pdf',
    submission_notes="Project proposal with detailed methodology"
)

# Check if late
if submission.is_late():
    submission.late_submission = True
    submission.late_penalty = deadline_event.late_submission_penalty
    submission.save()
```

### Example 3: Supervisor Reviews Submission

```python
# In supervisor review view
submission = EventSubmission.objects.get(id=submission_id)

if approved:
    submission.supervisor_approve(
        remarks="Well-structured proposal. Clear objectives.",
        rating=4
    )
else:
    submission.supervisor_reject(
        remarks="Needs more detail in methodology section."
    )
```

---

## 📝 Summary

These new features create a comprehensive feedback and submission workflow that:

✅ **Enhances Communication** between supervisors and students
✅ **Automates Analytics** with sentiment analysis
✅ **Enforces Quality** through two-stage approval
✅ **Tracks Progress** with integrated metrics
✅ **Manages Deadlines** with clear workflows
✅ **Protects Grades** through accountability

The system now provides a complete academic project management solution with real-time monitoring, automated analytics, and structured approval workflows.

---

**Version:** 1.1.0
**Last Updated:** November 13, 2025
**Status:** ✅ **PRODUCTION READY**

