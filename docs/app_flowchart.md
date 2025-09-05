flowchart TD
    Start[Start] --> Login[User Login]
    Login --> OAuth[Connect Email Accounts]
    OAuth --> UnifiedInbox[Unified Inbox Dashboard]
    UnifiedInbox --> FetchEmails[Fetch Emails via API]
    FetchEmails --> Categorize[AI Email Categorization]
    Categorize --> DashboardView[Display Categorized Emails]
    DashboardView --> UserActions[User Reviews and Actions]
    UserActions -->|Correct Category| Categorize
    UserActions -->|Request Summary| Summarize[Generate Email Summary]
    Summarize --> DashboardView
    UserActions -->|Draft Reply| DraftReply[Generate AI Reply Draft]
    DraftReply --> SaveDraft[Save Draft in Email Provider]
    SaveDraft --> DashboardView
    UserActions -->|Send Email| SendEmail[Send Email]
    SendEmail --> DashboardView

    subgraph BrowserExtension
      DashboardView --> ExtensionUI[Extension Quick Actions]
      ExtensionUI --> DraftReply
    end

    subgraph MeetingFlow
      DashboardView --> ScheduleMeeting[Schedule or Join Meeting]
      ScheduleMeeting --> JoinCall[Join Video Call]
      JoinCall --> RecordAudio[Record Audio]
      RecordAudio --> Transcribe[Transcribe Audio]
      Transcribe --> GenerateNotes[Generate Meeting Notes]
      GenerateNotes --> DraftFollowUp[Draft Follow-Up Email]
      DraftFollowUp --> SaveDraft
    end