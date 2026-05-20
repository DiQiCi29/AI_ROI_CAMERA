# 📅 Implementation Timeline & Action Plan

**Kế hoạch hoàn thành đồng bộ Backend + Android**

---

## 🎯 Mục Tiêu Chính

✅ Backend và Android App hoạt động **99% khớp** với thiết kế ban đầu (API_DESIGN.md)
✅ Real-time alerts hoạt động trơn tru
✅ Stream video hiệu quả
✅ Push notifications hoạt động
✅ Tất cả CRUD operations đầy đủ

---

## 📊 Effort Estimation

### Backend (AI_ROI_CAMERA)
| Phase | Tasks | Hours | Priority |
|-------|-------|-------|----------|
| **Phase 1** | WebSocket Events + Error Format + Zone Name | 6-8 | 🔴 CRITICAL |
| **Phase 2** | Logs Stats + FCM Service | 5-7 | 🟡 MEDIUM |
| **TOTAL** | | **11-15** | |

### Android (Flutter App)
| Phase | Tasks | Hours | Priority |
|-------|-------|-------|----------|
| **Phase 1** | Stream + Error + API Methods | 6-8 | 🔴 CRITICAL |
| **Phase 2** | Models + WebSocket + Package | 2-4 | 🟡 MEDIUM |
| **TOTAL** | | **8-12** | |

### **GRAND TOTAL: ~20-27 Hours**

---

## 📅 Proposed Timeline

### Week 1: Backend Critical Path (2-3 days)

**Day 1: WebSocket + Error Format**
- ⏰ 8:00 - Review changes
- ⏰ 9:00 - Implement `detection_service.py`
- ⏰ 12:00 - Update websocket.py
- ⏰ 14:00 - Create exception handlers
- ⏰ 17:00 - Test WebSocket events
- **Duration: 8 hours**

**Day 2: Enrich Alerts + Start Logs**
- ⏰ 9:00 - Add zone_name to alerts
- ⏰ 11:00 - Fix object_count calculation
- ⏰ 13:00 - Start logs stats implementation
- ⏰ 16:00 - Test alert responses
- **Duration: 6 hours**

**Day 3: Complete + Setup FCM**
- ⏰ 9:00 - Finish logs stats
- ⏰ 11:00 - Setup Firebase credentials
- ⏰ 14:00 - Implement FCM service
- ⏰ 17:00 - Integration testing
- **Duration: 7 hours**

**Result: Fully functional backend in 3 days**

---

### Week 1: Android Critical Path (2-3 days) - Parallel with Backend

**Day 1: Stream + Error Handling**
- ⏰ 9:00 - Review stream changes
- ⏰ 10:00 - Update ApiService for HLS
- ⏰ 12:00 - Create stream screen with video_player
- ⏰ 14:00 - Implement new error handling
- ⏰ 17:00 - Test stream playback
- **Duration: 7 hours**

**Day 2: Add Missing API Methods**
- ⏰ 9:00 - Add getZoneDetails()
- ⏰ 10:00 - Add updateZone()
- ⏰ 11:00 - Add deleteAlertMedia()
- ⏰ 12:00 - Add getLogs()
- ⏰ 14:00 - Test all CRUD operations
- **Duration: 6 hours**

**Day 3: Polish + Testing**
- ⏰ 9:00 - Update data models
- ⏰ 10:00 - Handle WebSocket events
- ⏰ 11:00 - Fix package name
- ⏰ 14:00 - Integration testing
- ⏰ 16:00 - Final verification
- **Duration: 6 hours**

**Result: Fully functional Android app in 3 days**

---

## 📋 Parallel Execution Plan

```
Week 1 Timeline:
┌──────────────────────────────────────────────────┐
│ BACKEND DEV (11-15 hours)                        │
│ Day 1: WebSocket + Error (8h)                    │
│ Day 2: Enrich Alerts + Logs (6h)                 │
│ Day 3: FCM + Integration (7h)                    │
└──────────────────────────────────────────────────┘
                   ↓
        Running in PARALLEL
                   ↓
┌──────────────────────────────────────────────────┐
│ ANDROID DEV (8-12 hours)                         │
│ Day 1: Stream + Error (7h)                       │
│ Day 2: API Methods (6h)                          │
│ Day 3: Polish + Testing (6h)                     │
└──────────────────────────────────────────────────┘
```

**Both teams work independently and integrate at the end**

---

## ✅ Critical Path Dependencies

```
Backend:
  1. WebSocket Events ← Foundation for real-time
  2. Error Format ← Used by Android for error handling
  3. Zone Name enrichment ← UI display depends on it
  4. Logs Stats ← Dashboard feature
  5. FCM Service ← Push notifications

Android:
  1. Stream handling update ← Can work independently
  2. Error handling fix ← Once backend deploys error format
  3. Add API methods ← Backend methods must exist
  4. Data models ← Once API responses finalized
  5. Package name ← Can do anytime
```

**Recommendation: Run in parallel, integration at end of each day**

---

## 🔄 Daily Integration Points

### Each Day End
- ✅ Run integration tests
- ✅ Test end-to-end workflows
- ✅ Verify error cases
- ✅ Check API contracts match

### Test Scenarios
1. **Login Flow**
   - Android → Backend login
   - Receive token
   - Setup authorization

2. **Real-time Alerts**
   - Backend detects intrusion
   - Sends WebSocket event
   - Android receives and displays
   - Android receives FCM notification (if applicable)

3. **Zone Management**
   - Android create zone
   - Backend saves
   - Android fetch and display
   - Android update zone
   - Android delete zone

4. **Stream Video**
   - Android request stream URLs
   - Backend returns HLS/RTSP URLs
   - Android plays video

5. **Error Scenarios**
   - Invalid credentials → 401
   - Zone not found → 404
   - Server error → 500
   - All return proper error format

---

## 📝 Phase-by-Phase Checklist

### PHASE 1: CRITICAL (Days 1-2, ~14 hours combined)

#### Backend
- [ ] Implement `app/services/detection_service.py`
- [ ] Update `app/api/v1/routes/websocket.py`
- [ ] Create `app/core/exceptions.py`
- [ ] Update `app/main.py` with exception handlers
- [ ] Update `app/api/v1/routes/alerts.py` - add zone_name + fix object_count
- [ ] Test WebSocket events
- [ ] Test error response format
- [ ] Test alert with zone_name

#### Android
- [ ] Update `ApiService.dart` - getStreamUrls()
- [ ] Create new `StreamScreen` with video_player
- [ ] Update error handling in ApiService
- [ ] Create `ApiException` class
- [ ] Create `ApiErrorHandler` helper
- [ ] Test login with errors
- [ ] Test stream playback
- [ ] Update pubspec.yaml with video_player
- [ ] Test error display

---

### PHASE 2: HIGH PRIORITY (Day 2-3, ~10 hours combined)

#### Backend
- [ ] Update `app/api/v1/routes/logs.py` - enhance stats
- [ ] Add queries for week_count, most_active_zone, peak_hour, by_zone
- [ ] Setup Firebase Admin SDK
- [ ] Create `app/services/fcm_service.py`
- [ ] Integrate FCM into alert creation
- [ ] Test logs stats endpoint
- [ ] Test FCM sending (if credentials available)

#### Android
- [ ] Add `getZoneDetails()` method
- [ ] Add `updateZone()` method
- [ ] Add `deleteAlertMedia()` method
- [ ] Add `getLogs()` method
- [ ] Update `ZoneModel` - add updated_at
- [ ] Update WebSocket handler for "connected" event
- [ ] Fix package name consistency
- [ ] Test all CRUD operations
- [ ] Test logs/history list

---

### PHASE 3: POLISH (Day 3, ~5 hours combined)

#### Backend
- [ ] Performance optimization
- [ ] Add logging/monitoring
- [ ] Documentation updates
- [ ] Final integration tests
- [ ] Deploy to test server

#### Android
- [ ] UI/UX improvements
- [ ] Performance optimization
- [ ] Add retry logic for failures
- [ ] Final integration tests
- [ ] Build APK for testing
- [ ] Test on real device

---

## 🧪 Integration Testing Plan

### Day 1 End: Basic Connectivity
```bash
1. Backend running on localhost:8000
2. Android app configured with correct API URL
3. Login works
4. No connection errors
5. Basic auth header sending
```

### Day 2 End: Feature Complete
```bash
1. WebSocket connection works
2. Stream video plays
3. Zone CRUD operations work
4. Error handling works correctly
5. Alert list displays with zone_name
6. Logs stats show all fields
```

### Day 3 End: Full Integration
```bash
1. Real-time alerts work end-to-end
2. FCM notifications (if available)
3. All error cases handled
4. Performance acceptable
5. Battery/memory usage reasonable
6. Ready for user testing
```

---

## 🚀 Deployment Plan

### Step 1: Staging Deployment
1. Deploy backend to staging server
2. Update Android to point to staging
3. Run full test suite
4. Get team approval

### Step 2: Production Deployment
1. Backup current database
2. Deploy backend changes
3. Verify health check
4. Release Android update through play store
5. Monitor for errors

### Step 3: Rollback Plan (If Needed)
1. Backend: Git revert to previous version
2. Android: Pull previous APK from distribution
3. Database: Restore from backup if needed

---

## 👥 Team Structure

### Option A: 2 Teams (Parallel)
- **Backend Team** (1-2 devs) - AI_ROI_CAMERA
- **Android Team** (1-2 devs) - Flutter App
- **QA** (1 person) - Integration testing

### Option B: Single Full-Stack Dev
- Handle both backend and Android sequentially
- **Timeline**: ~25-30 hours = 3-4 days full-time

---

## 📞 Communication Protocol

### Daily Standup (10 min)
- What was done
- What's blocking
- What's planned for next hours

### End of Day Review (30 min)
- Test results
- Issues found
- Plan adjustments
- Approvals for integration

### Weekly Retrospective (1 hour)
- What went well
- What could improve
- Lessons learned

---

## ⚠️ Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Scope Creep** | Delays | Fixed feature list, no new features during implementation |
| **Integration Issues** | Delays | Daily integration testing, clear API contracts |
| **Database Issues** | Data loss | Backup before changes, test migrations |
| **Firebase Setup** | FCM failure | Setup early, have fallback notification method |
| **Network Issues** | Testing delays | Use local VPN, mock server if needed |

---

## 📊 Success Metrics

✅ **Code Quality**
- Zero critical errors
- 90%+ test coverage for new code
- Code review approval

✅ **Functionality**
- All endpoints working
- Real-time alerts functional
- Error handling complete
- Performance acceptable

✅ **User Experience**
- No crashes
- Fast response times (<2s)
- Clear error messages
- Intuitive UI

---

## 📋 Pre-Implementation Checklist

Before starting, ensure:
- [ ] Both teams have reviewed all documentation
- [ ] Development environments are setup
- [ ] Database backups configured
- [ ] Firebase credentials obtained (if needed)
- [ ] Testing devices/emulators ready
- [ ] Git branches created for development
- [ ] CI/CD pipelines configured (if applicable)
- [ ] Team members assigned
- [ ] Schedule confirmed
- [ ] Communication tools setup (Slack, Teams, etc.)

---

## 📞 Key Documents Reference

| Document | Purpose | Audience |
|----------|---------|----------|
| **COMPREHENSIVE_SYNC_PLAN.md** | Overview of all changes | Everyone |
| **BACKEND_IMPLEMENTATION_GUIDE.md** | Step-by-step backend changes | Backend Dev |
| **ANDROID_IMPLEMENTATION_GUIDE.md** | Step-by-step Android changes | Android Dev |
| **API_DESIGN.md** | Original API specification | Reference |
| **DESIGN_VS_IMPLEMENTATION_ANALYSIS.md** | What needs to change | Decision makers |

---

## 🎓 Knowledge Transfer

After implementation:
1. Create video walkthroughs of key features
2. Document any workarounds or quirks
3. Setup monitoring and alerting
4. Create user documentation
5. Train support team

---

## 💰 Resource Requirements

### Infrastructure
- Staging server (for testing)
- Firebase project (for FCM)
- Database backup system
- Monitoring tools

### Software
- Video player plugin dependencies
- Firebase Admin SDK
- Testing frameworks

### Personnel
- 2-4 developers
- 1 QA engineer
- 1 DevOps (for deployment)
- 1 Product owner (for decisions)

---

## 📈 Expected Outcomes

### Upon Completion
✅ 95%+ API compliance with API_DESIGN.md
✅ Real-time alerts fully functional
✅ Push notifications working
✅ Stream video playing smoothly
✅ Zero critical bugs
✅ Full test coverage
✅ Complete documentation

### Performance Targets
- ⚡ API response time: <500ms
- 📱 App startup time: <3s
- 🔌 WebSocket latency: <100ms
- 🎥 Stream startup: <2s
- 🔋 Battery drain: <5% per hour

---

## 🎉 Completion Criteria

### Code Review Approval
- [ ] All code reviewed and approved
- [ ] Tests passing
- [ ] No linting errors

### Functionality Verification
- [ ] All endpoints tested
- [ ] All UI screens working
- [ ] Error handling complete
- [ ] WebSocket real-time verified

### Performance Verification
- [ ] Load testing passed
- [ ] Memory profiling acceptable
- [ ] Battery drain acceptable

### Documentation Complete
- [ ] Code documented
- [ ] API endpoints documented
- [ ] Known issues documented
- [ ] Deployment guide created

---

**Timeline Version:** 1.0  
**Created:** May 17, 2026  
**Ready for Implementation:** YES ✅

---

**Next Steps:**
1. Review this plan with team
2. Confirm timelines and resources
3. Create git branches
4. Start implementation (Day 1)
5. Daily integration testing
6. Deploy to staging (Day 4)
7. User testing (Week 2)
8. Production release (Week 3)
