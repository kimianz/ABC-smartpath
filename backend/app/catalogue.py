"""Fictional interview catalogue. Exact commercial facts live here, never in model weights.
Prices are illustrative per learner inclusive of assumed VAT. Team quotes require staff review.
"""
from datetime import date

def course(id,title,description,category,level,duration,price,skills,required=(),formats=('online','classroom'),audiences=('individual','team'),capacity=24,offset=0):
    return dict(id=id,title=title,description=description,category=category,level=level,duration=duration,price_gbp=price,skills=list(skills),required_skills=list(required),prerequisites=['Working knowledge of '+s for s in required] or ['No specialist prior knowledge required'],formats=list(formats),audiences=list(audiences),capacity=capacity,dates=[f'2026-11-{9+offset:02d}',f'2026-11-{23+offset:02d}'],availability='Sample scheduled cohort. Places require staff confirmation.')
COURSES=[
course('AI101','AI for Business Teams','Understand artificial intelligence in everyday business. Identify safe opportunities, assess risks, map an HR or operations workflow and develop a small adoption plan. Designed for nontechnical employees starting together.','AI','beginner','1 day',295,['ai literacy','business use cases','responsible ai']),
course('AI102','Generative AI at Work','Use generative AI to draft, summarise and analyse routine information. Practise prompt writing, validate outputs and protect confidential data. Hands-on workplace productivity for HR, administration and customer service teams.','AI','beginner','2 days',495,['generative ai','prompting','workplace productivity']),
course('AI103','Responsible AI Adoption Workshop','Plan safe AI adoption as a team. Compare processes, define human oversight, assess privacy and agree an actionable policy. Practical workshop for managers and staff with no coding requirement.','AI','beginner','1 day',350,['responsible ai','ai policy','business use cases'],audiences=('team',),capacity=20),
course('PY101','Python Foundations','Learn variables, functions, files and debugging through practical automation exercises. Suitable for new programmers.','Programming','beginner','5 days',895,['python','automation']),
course('PY201','Python for Data Analysis','Clean tabular data, join datasets and build reproducible analysis with pandas. Requires Python programming fundamentals.','Data','intermediate','3 days',795,['pandas','data analysis','python'],required=('python',)),
course('DA101','Data Analytics Essentials','Frame business questions, interpret charts, clean spreadsheets and communicate evidence. No coding is required.','Data','beginner','2 days',425,['data analysis','data literacy']),
course('XL101','Excel for Everyday Work','Build reliable spreadsheets using formulas, filtering and clear charts. Suitable for learners new to spreadsheets.','Business','beginner','1 day',195,['excel','spreadsheets']),
course('XL201','Advanced Excel and Power Query','Automate data cleaning, use pivot tables and improve reporting with Power Query. Requires Excel fundamentals.','Data','intermediate','2 days',395,['excel','power query','reporting'],required=('excel',)),
course('BI101','Power BI Reporting','Create interactive business reports, build relationships and publish dashboards. Requires confidence with Excel.','Data','intermediate','3 days',695,['power bi','dashboards','reporting'],required=('excel',)),
course('CY101','Cybersecurity Awareness','Recognise phishing, protect credentials and respond to everyday security incidents. Practical exercises for all staff.','Security','beginner','Half day',125,['security awareness','phishing']),
course('DM101','Digital Marketing Essentials','Plan campaigns, define audiences and measure conversion across search, email and social channels.','Marketing','beginner','2 days',395,['digital marketing','campaign measurement']),
course('LD101','Leading Effective Teams','Set expectations, coach colleagues and manage performance fairly. Built for new and aspiring line managers.','Leadership','beginner','2 days',475,['leadership','coaching']),
course('PM101','Practical Project Management','Scope projects, manage dependencies, estimate effort and report risks using a practical delivery plan.','Business','beginner','2 days',450,['project management','risk management']),
course('ML301','Applied Machine Learning with Python','Train, evaluate and interpret supervised learning models. Requires Python and statistical foundations.','AI','advanced','4 days',1195,['machine learning','model evaluation'],required=('python','statistics'),capacity=12)
]
# Descriptive knowledge is deliberately carried in description because this is
# the persisted/retrieved field. Structured eligibility and commercial facts above
# remain unchanged. Policies below are fictional scenario decisions, not ABC facts.
_COURSE_DETAIL = {'AI101': 'Learning outcomes: distinguish AI, machine learning and generative AI in plain language; identify '
          'useful business tasks; assess risks and decide when human judgement is essential. Typical '
          'activities include mapping a fictional HR enquiry process, comparing an AI-assisted task with its '
          'manual version and producing a small adoption canvas with a measurable objective. This course '
          'suits nontechnical staff and managers seeking a shared foundation, rather than developers '
          'learning to build models. A laptop or desktop with a modern browser and basic keyboard skills is '
          'sufficient; no coding or specialist software is required. Only fictional or non-confidential '
          'examples are used. Online delivery is live and instructor-led; classroom delivery follows the '
          'same learning goals. The one-day duration covers introductory practice, not mastery or '
          'implementation of an organisation-wide AI programme.',
 'AI102': 'Learning outcomes: write a clear task and context, improve a prompt iteratively, check an AI '
          'output against an approved source and recognise when not to use generative AI. Exercises use '
          'fictional emails, meeting notes and policy extracts to practise drafting, summarisation and '
          'structured information extraction, with a human verification checklist. Designed for beginners in '
          'HR, administration, operations and customer service who want practical workplace productivity '
          'skills. Bring a laptop or desktop, a modern browser and basic file-handling skills. The exercise '
          'environment and any account access must be confirmed before the course; a paid personal AI '
          'subscription is not an assumed prerequisite. Never bring confidential staff or customer records. '
          'Two teaching days provide guided practice and an action plan, not a guarantee that every task can '
          'be automated. Online sessions are live instructor-led, not a self-paced video library.',
 'AI103': 'Learning outcomes: select an appropriate AI use case, recognise privacy and reliability risks, '
          'define review responsibilities and draft a proportionate internal-use checklist. A team works '
          'through a fictional AI-assisted HR workflow, identifies failure points and agrees an adoption '
          'plan with owners and review gates. This is a team-only workshop for managers and staff building '
          'shared expectations; it is not a coding course, legal advice or an external compliance '
          'certification. No specialist prior knowledge is needed. A laptop or desktop with a modern browser '
          'is useful for shared templates; participants should use fictional examples and avoid personal or '
          'confidential business records. The one-day workshop supports a first policy discussion rather '
          'than certifying an organisation as compliant. Live online and classroom versions have the same '
          'intended outcomes. The team capacity is a cohort limit, not a promise of reserved seats.',
 'PY101': 'Learning outcomes: use variables, lists and dictionaries; write small functions; read and write '
          'files; interpret errors and test a simple script. Typical exercises transform fictional text '
          'files, calculate summary figures and automate a repetitive file-handling task. This beginner '
          'course suits office staff moving into automation and learners taking their first programming '
          'steps; Python experience is not required. Learners need basic computer and folder navigation '
          'skills, a laptop or desktop on which they can run the supplied Python environment, and permission '
          'to install software or access an agreed browser environment. Setup instructions and suitability '
          "for the learner's device must be confirmed before attendance. Five teaching days allow "
          'incremental practice and debugging, not a promise of professional developer competence. Both '
          'listed delivery formats are instructor-led. Learners can ask about setup or access needs through '
          'a consultation before choosing the course.',
 'PY201': 'Learning outcomes: load tabular files with pandas, inspect data quality, handle missing values, '
          'join related tables and explain a reproducible analysis. Exercises clean fictional enrolment '
          'data, combine two datasets and produce a documented summary rather than a black-box result. '
          'Suitable for learners who already write basic Python functions and work with lists, loops and '
          'files; Python Foundations or equivalent experience is the intended preparation. Learners must '
          'confirm their Python skill rather than relying only on a general intermediate label. Bring a '
          'laptop or desktop with a working Python environment able to run pandas; software setup is checked '
          'before the course. Three teaching days concentrate on analysis practice, not advanced machine '
          'learning or production data engineering. Work uses sample data only. Live online and classroom '
          'sessions use the same core exercises, with staff confirming any device or accessibility '
          'arrangements.',
 'DA101': 'Learning outcomes: turn a business question into a measurable analysis, identify common '
          'data-quality problems, choose an appropriate chart and explain uncertainty without overstating a '
          'finding. Exercises inspect fictional enquiry and booking tables, clean a small spreadsheet and '
          'write a short evidence-based recommendation. Intended for staff and managers new to data '
          'analysis; programming and advanced mathematics are not prerequisites. Basic confidence opening '
          'files and using a computer is useful. Learners need a laptop or desktop with a spreadsheet '
          'application capable of the supplied exercises; the appropriate application and file format should '
          'be confirmed in advance. The two-day course focuses on interpretation and responsible '
          'communication, rather than Python coding, specialist statistics or a guarantee of a data analyst '
          'job. Live online and classroom formats are instructor-led and share the same learning outcomes.',
 'XL101': 'Learning outcomes: organise a simple workbook, enter and copy formulas safely, use sorting and '
          'filtering, create a clear chart and check for common spreadsheet errors. Exercises build a '
          'fictional training budget and a small attendance tracker, then check totals against source '
          'values. Suitable for learners new to spreadsheets or returning after a gap; no Excel skill is '
          'required. Basic keyboard, mouse and file-opening skills are useful. Learners need access to a '
          'laptop or desktop and an Excel environment compatible with the supplied exercises; staff should '
          'confirm the version before booking, especially for browser or Mac users. The one-day course '
          'provides foundational practice, not advanced reporting or Power Query. Live online sessions '
          'include instructor guidance and are not self-paced recordings. A quote or consultation can '
          'clarify equipment and access needs before a booking decision.',
 'XL201': 'Learning outcomes: clean and reshape repeatable data, build a pivot-table summary, combine '
          'suitable source files and check a refreshable reporting workflow. Exercises transform fictional '
          'monthly training records and compare manual cleaning with Power Query steps. Learners need '
          'working Excel fundamentals, including formulas, tables and filtering; Excel for Everyday Work or '
          'equivalent experience is the intended preparation. This is not a first spreadsheet course. A '
          'laptop or desktop with an Excel version supporting the planned Power Query exercises is required; '
          'features differ by operating system and version, so Mac or browser users should confirm '
          'suitability with staff before booking. Two teaching days provide a reusable reporting pattern, '
          'not every advanced Excel function. Both listed formats are instructor-led. Sample datasets are '
          'provided; learners should not upload confidential organisational workbooks.',
 'BI101': 'Learning outcomes: import and transform sample data, create a simple relationship model, build '
          'measures and design an interactive report with understandable filters. Exercises use fictional '
          'course and booking tables, check totals and prepare a report for a manager. Requires confident '
          'Excel use, including tables and basic formulas; learners without that foundation should start '
          'with Excel preparation. The course uses a suitable Windows environment for Power BI Desktop. '
          'Mac-only or managed-device users must ask staff about an agreed compatible environment before '
          'booking; alternative equipment is not automatically included. The publishing workflow is '
          'explained, but access to a real organisational tenant, licence or public dashboard is not '
          'included or promised. Three teaching days focus on a working introductory report, not enterprise '
          'deployment. Live online and classroom formats use the same core sample data and learning '
          'outcomes.',
 'CY101': 'Learning outcomes: recognise common phishing signals, use safer account practices, identify a '
          'suspicious request and describe an appropriate reporting action. Exercises compare fictional '
          'emails and messages, review password and multifactor-authentication scenarios and practise a calm '
          'response to a suspected incident. Suitable for all staff with no specialist security experience. '
          'A laptop or desktop with a browser is useful for the activities; the course does not require '
          'penetration-testing tools or access to real systems. The half-day session develops awareness and '
          'decision-making, not professional cybersecurity qualification, incident-response certification or '
          "a guarantee that attacks will be prevented. Learners should follow their own organisation's "
          'approved reporting process; the class does not replace it. Live online and classroom delivery are '
          'instructor-led, using harmless examples rather than live attacks.',
 'DM101': 'Learning outcomes: define a campaign audience and objective, choose suitable channels, map a '
          'simple customer journey and interpret conversion measures. Exercises develop a fictional '
          'training-course campaign, compare sample channel results and draft a small experiment with a '
          'budget assumption. Designed for beginners, small-business staff and people taking on marketing '
          'responsibilities; specialist analytics or coding experience is not required. Learners need a '
          'laptop or desktop with a browser and basic spreadsheet confidence for the sample figures. No real '
          'advertising account, customer mailing list, paid campaign spend or third-party integration is '
          'included. Two teaching days develop an initial campaign plan rather than promise sales growth, '
          'search ranking or marketing accreditation. Live online and classroom sessions cover the same core '
          "exercises. Any use of an organisation's actual customer data would need its own authorisation and "
          'is not part of the sample activities.',
 'LD101': 'Learning outcomes: set clear expectations, prepare a constructive feedback conversation, use a '
          'simple coaching structure and agree fair next actions. Exercises include fictional team '
          'scenarios, a role-play conversation and a practical plan for a first management responsibility. '
          'Suits new or aspiring line managers and staff moving into supervision; previous management '
          'experience is not required. A laptop or desktop with a browser is useful for online participation '
          'and templates; classroom equipment arrangements should be confirmed with staff. Learners are not '
          'required to disclose sensitive employee cases. Two teaching days provide guided practice and '
          "reflection, not a professional management award or a substitute for an employer's HR policies. "
          'Both formats are instructor-led. Anyone who would find role-play or a particular activity '
          'difficult can request a discussion of participation options without providing medical detail to '
          'the AI adviser.',
 'PM101': 'Learning outcomes: define a clear project outcome and scope, break work into tasks, estimate '
          'effort, identify dependencies and communicate risks and progress. Exercises plan a fictional '
          'internal training rollout, create a simple milestone schedule and discuss a scope-change '
          'decision. Suitable for beginners managing a first project or supporting a delivery team; no '
          'project management qualification is required. Bring a laptop or desktop with a browser and a way '
          'to work with the supplied planning templates; a paid specialist project tool is not assumed. Two '
          'teaching days develop a practical starter plan and governance habits, not mastery of every '
          'delivery method. The course does not include an external certification exam or promise a '
          'recognised accreditation. Live online and classroom sessions share the same outcomes, using '
          'sample project information rather than confidential client plans.',
 'ML301': 'Learning outcomes: prepare a labelled dataset, separate training and evaluation data, compare '
          'supervised-learning baselines and explain model errors and limitations. Exercises train a small '
          'scikit-learn model on a fictional or openly usable sample dataset, check for leakage and discuss '
          'appropriate metrics. This advanced course requires working Python programming skills and '
          'statistical foundations; those prerequisites must be confirmed. A beginner interested in AI '
          'should choose an introductory AI course or build Python and statistics preparation first. '
          'Learners need a laptop or desktop capable of running the agreed Python and scikit-learn '
          'environment; a paid cloud GPU is not an assumed requirement. Four teaching days provide a '
          'supervised-learning workflow, not production ML operations, a research qualification or '
          'guaranteed predictive accuracy. The smaller cohort supports practical troubleshooting. Both '
          'delivery formats are instructor-led; software readiness is checked before attendance.'}
for _course in COURSES:
    _course["description"] += " " + _COURSE_DETAIL[_course["id"]]

FAQS = [{'id': 'FAQ-QUOTE',
  'text': 'Team enquiries require a staff-reviewed quotation. Published course prices are per learner, '
          'inclusive of assumed VAT in this fictional scenario. A quote can confirm the scope and total; no '
          'volume discount, negotiated rate or commercial proposal is authorised automatically.'},
 {'id': 'FAQ-BOOK',
  'text': 'Course dates and cohort capacities are fictional demonstration inventory, not live booking '
          'availability. Enrol, quote and consultation actions create enquiries; they do not reserve or '
          'purchase a seat. Staff must confirm the schedule, available places and next steps.'},
 {'id': 'FAQ-PRIVACY',
  'text': 'You can explore courses and receive recommendations without providing contact details. Contact '
          'information is requested only when you choose a service such as a quote, consultation, enrolment '
          'enquiry or recommendation email. Service contact and optional marketing permission are separate. '
          'Staff can record an opt-out or handle a deletion request; do not share sensitive personal '
          'information in chat.'},
 {'id': 'FAQ-DELIVERY',
  'text': 'Online means live instructor-led sessions, not a self-paced video course. Classroom delivery is '
          'also instructor-led; the location must be confirmed by staff and no venue address is promised '
          'here. Both formats aim for the same listed learning outcomes. Bespoke dates or delivery '
          'arrangements require a reviewed proposal.'},
 {'id': 'FAQ-HELP',
  'text': 'For help, describe the issue or ask about a course in the training finder. If you need a person '
          'to review timing, suitability, equipment or an unusual request, choose Ask a human for help in the '
          'finder or Contact our team in the footer. No course recommendation is required. Submit your '
          'question and contact details with service consent. This stores an enquiry for staff review; the '
          'prototype does not provide a live telephone helpline, helpdesk email address or guaranteed '
          'response time.'},
 {'id': 'FAQ-START',
  'text': 'If you are unsure where to start, say what task you want to do better and what you already know. '
          'For example, improving office productivity, understanding data or learning to code are different '
          'goals. The guided finder asks relevant follow-up questions progressively; you can switch to chat '
          'and skip optional preferences such as delivery format or timing. You do not need to know the right course name.'},
 {'id': 'FAQ-LEVEL',
  'text': 'Beginner courses introduce a subject without specialist prior knowledge. Intermediate courses '
          'assume the named foundations, such as Python for Python for Data Analysis or Excel for Advanced '
          'Excel and Power Query. Applied Machine Learning with Python is advanced and requires Python plus '
          'statistics. A general experience label does not confirm a specific prerequisite: tell the adviser '
          'which skills you actually have.'},
 {'id': 'FAQ-JARGON',
  'text': 'AI means artificial intelligence: software used for tasks such as recognising patterns or '
          'generating content. Generative AI creates outputs such as text from instructions called prompts. '
          'Data analytics means using data to answer questions; a dashboard presents measures visually. '
          'Python is a programming language, while Excel is a spreadsheet tool. Explain your task in '
          'everyday language if these terms are unfamiliar; the finder should clarify rather than test your '
          'vocabulary.'},
 {'id': 'FAQ-CHOICE',
  'text': 'AI for Business Teams builds a nontechnical foundation and a small adoption plan. Generative AI '
          'at Work concentrates on practical prompting and workplace tasks. Responsible AI Adoption Workshop '
          'is for teams agreeing safeguards and responsibilities. Python Foundations teaches programming; it '
          'is not required for the introductory workplace AI courses. State your intended task so the '
          'adviser can explain the best fit.'},
 {'id': 'FAQ-UNCLEAR',
  'text': 'If your request is unclear or contradictory, the adviser should ask a useful clarification '
          'instead of guessing. Explain whether training is for you or a team, the goal, current experience '
          'and any essential delivery or timing constraint. If no course meets those needs, fewer than three '
          'recommendations or a consultation is appropriate; a similar-sounding course is not automatically '
          'suitable.'},
 {'id': 'FAQ-TEAM',
  'text': 'Team training needs a confirmed number of employees and their relevant experience. A published '
          'capacity is the maximum sample cohort size, not a count of places remaining. Most sample courses '
          'have a capacity of 24; Responsible AI Adoption Workshop is team-only with a capacity of 20, and '
          'Applied Machine Learning with Python has a capacity of 12. A larger group needs staff review of '
          'cohorts or a bespoke proposal.'},
 {'id': 'FAQ-BUDGET',
  'text': 'The finder treats the optional budget as the total enquiry budget, not an amount per person. '
          'Published course prices are per learner, so a team estimate is the per-learner price multiplied '
          'by the number of learners, before any separately reviewed arrangements. Say clearly if you meant '
          'a per-person budget. Unknown prices or discounts must be referred to staff, not invented.'},
 {'id': 'FAQ-DATES',
  'text': 'The course details show the stored sample dates. A requested timeline such as within six weeks is '
          'checked against those dates and the other eligibility requirements. Dates and capacities are not '
          'a live inventory feed. Staff must confirm actual arrangements; if no suitable date is shown, '
          'request a consultation rather than assume that a new date or extra places are available.'},
 {'id': 'FAQ-DURATION',
  'text': 'Durations are the teaching time labels listed for each course: half day, one day or several days. '
          'A five-day course does not automatically mean five consecutive calendar days, and a two-day '
          'course does not promise a particular daily timetable. Staff confirm session times, breaks and '
          'scheduling. The durations describe guided learning, not a guarantee of mastery, certification or '
          'time saved at work.'},
 {'id': 'FAQ-EQUIPMENT',
  'text': 'For live online training, learners normally need a laptop or desktop, a reliable internet '
          'connection and audio access. A phone alone may be unsuitable for practical software exercises. '
          'Software and installation permission vary by course, so check the course description and ask '
          'staff to confirm your device and access before booking. Loan equipment, software licences and '
          'paid accounts are not automatically included.'},
 {'id': 'FAQ-MAC',
  'text': 'Mac suitability depends on the course and exercise software. Introductory AI, leadership and '
          'project-planning activities can use an agreed browser environment. Excel and Power Query features '
          'vary by version and operating system, so staff should confirm compatibility. Power BI Reporting '
          'uses a suitable Windows environment for Power BI Desktop; Mac-only learners need an agreed '
          'arrangement before booking. No replacement device or hosted Windows service is promised '
          'automatically.'},
 {'id': 'FAQ-ACCESS',
  'text': 'If you need accessible materials, a different activity format or support with participation, '
          'request a consultation so staff can discuss what is feasible before booking. You do not need to '
          'disclose a diagnosis or medical details to the AI adviser. Captions, assistive-technology '
          'compatibility, venue access or individual adjustments must be confirmed by staff; they are not '
          'guaranteed simply because a course is listed.'},
 {'id': 'FAQ-ASSESSMENT',
  'text': 'Courses use guided exercises and discussion to check understanding. The catalogue does not '
          'promise a formal exam, graded award, certificate or third-party accreditation. If evidence of '
          'attendance or a particular credential is important, ask staff to confirm what can be provided '
          'before booking. Completing an exercise is not the same as holding an externally recognised '
          'qualification.'},
 {'id': 'FAQ-CAREER',
  'text': 'Training can develop relevant skills and help you practise a task, but it does not guarantee a '
          'job, promotion, salary increase, business result or professional status. For a career change, '
          'explain your starting skills and target role so the adviser can suggest a sensible first step. '
          'Staff can discuss course suitability; this sample service is not a recruitment agency or a '
          'job-placement programme.'},
 {'id': 'FAQ-PAYMENT',
  'text': 'The prototype does not take card details or process payments. Enrol is an enrolment enquiry, not '
          'a completed checkout. Staff must review the request and confirm price, payment arrangements and '
          'any terms before a purchase. Do not enter bank or card information in chat. No instalment plan, '
          'invoice credit period or funding eligibility is promised by the adviser.'},
 {'id': 'FAQ-CANCEL',
  'text': 'Cancellation, refunds and rescheduling require staff review. The fictional catalogue does not '
          'define a refund entitlement, cancellation deadline, transfer fee or guaranteed replacement date. '
          'Request a consultation or use your existing service enquiry so staff can confirm applicable terms '
          'before you commit. The AI adviser must not invent a refund policy or approve a cancellation '
          'payment.'},
 {'id': 'FAQ-QUOTE-VS-CONSULT',
  'text': 'Choose Get a Quote when you want staff to review training scope and a price proposal, especially '
          'for a team. Choose Book a Consultation when suitability, prerequisites, equipment or timing needs '
          'discussion. Enrol records interest in joining a course; it does not reserve a place. Email My '
          'Recommendations requests a service summary. These actions request staff follow-up rather than '
          'completing an external booking.'},
 {'id': 'FAQ-EMAIL',
  'text': 'Requested service summaries and approved follow-ups are recorded in a local test outbox in this '
          'prototype. No live email provider or delivery to a real inbox is configured. Commercial quotes '
          'need staff review, and service consent does not mean marketing subscription. The adviser must not '
          'say an email was delivered, a meeting booked or a payment taken merely because an enquiry was '
          'saved.'},
 {'id': 'FAQ-FOLLOWUP',
  'text': 'Follow-up reminders must respect the service request and stop after a reply, booking or opt-out '
          'is recorded by staff. Staff review sensitive commercial drafts and can edit, approve or reject '
          'them. The prototype has no public self-service unsubscribe link or external inbox integration; a '
          'recorded staff status is the supported stop mechanism. Marketing permission remains separate.'},
 {'id': 'FAQ-FACTS',
  'text': 'The adviser should answer course questions from the approved catalogue and service policies, with '
          'traceable course or FAQ references. Prices, prerequisites, dates and capacity come from stored '
          'facts. If information is missing, uncertain or outside the catalogue, it should say so and offer '
          'a relevant clarification or staff consultation. It must not invent an accreditation, venue, '
          'available seat, discount or company achievement.'}]
