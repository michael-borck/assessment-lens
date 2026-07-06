# Signal-Based Assessment: A Position Paper

**Grounding automated evidence extraction in Evidence-Centered Design**

---

## Purpose of this document

This paper explains the thinking behind the signal-based assessment tool: what it does, what it deliberately does not do, and the research tradition it draws on. It is written for markers, unit coordinators, assessment committees, and anyone who wants to understand why the tool is designed the way it is before trusting it in their own marking workflow.

The short version: the tool automates the *gathering of evidence* about student work. It never automates the *judgment* about what that evidence means. That division of labour is not a compromise or a hedge. It is the core design principle, and it is grounded in sixty years of assessment research.

## The problem

Marking at scale forces a trade-off. Large cohorts mean markers spend most of their time on mechanical observation: counting, checking, scanning, and locating, before they can get to the part that actually requires their expertise, which is interpretation and judgment. Under time pressure, the observation work crowds out the judgment work. Consistency suffers, feedback thins out, and experienced markers burn their attention on tasks a machine could do.

The obvious response, fully automated scoring, solves the workload problem by removing the human. Decades of research (summarised below) tells us this trades one problem for a worse one: automated scores systematically under-represent what we actually value in student work, and they are vulnerable to being gamed.

Signal-based assessment takes a different position. Automate the observation. Keep the judgment human.

## What the tool does

For each student artefact, whether a written document, a codebase, a webpage, or a video, the tool computes a set of **signals**: automatically extracted, observable properties of the work. For text, these include readability indices, sentence and paragraph statistics, lexical diversity, and structural measures. For code, they include complexity metrics, style conformance, and test coverage. For webpages, accessibility and semantic structure checks. For video, delivery measures such as speech rate and pacing.

Each signal is mapped to one or more rubric criteria. The marker sees the student's work alongside the signals relevant to each criterion, and then does what only a human can do: interprets the signals in context and assigns the mark.

We use the term *signals* deliberately. In machine learning, "features" are inputs consumed by a model that produces the judgment. Nothing in this tool consumes the signals. They are presented to a person. A signal is something detected that requires interpretation, and that framing is exactly right: a low readability score on a reflective essay might indicate poor writing, or it might indicate sophisticated technical vocabulary used appropriately. The signal cannot tell the difference. The marker can.

## The theoretical foundation: Evidence-Centered Design

The tool's architecture maps directly onto **Evidence-Centered Design** (ECD), the assessment framework developed by Mislevy, Steinberg and Almond (2003). ECD describes any assessment, from a multiple-choice quiz to a portfolio review, as a chain of reasoning:

1. **Work product.** The student produces an artefact: an essay, a repository, a site, a recording.
2. **Evidence identification.** Observable variables are extracted from the work product. This can be done by a human, a machine, or both.
3. **Evidence accumulation.** The observables are weighed and synthesised into a claim about the student's proficiency against defined criteria.

ECD's crucial insight is that steps 2 and 3 are separable. Identifying evidence and judging evidence are different activities with different requirements. Evidence identification rewards consistency, coverage, and tirelessness, which are machine strengths. Evidence accumulation against a rubric requires contextual understanding, construct knowledge, and accountability, which are human strengths.

This tool automates step 2 and leaves step 3 entirely with the marker. In ECD terms, the signals are observable variables, the rubric mapping is the evidence model, and the marker performs evidence accumulation. Because ECD is domain-agnostic, the same architecture holds whether the work product is prose, code, or video. The framework does not care what the artefact is, only that evidence is systematically identified and then judged.

## The research lineage

The idea that measurable properties of student work carry information about its quality is not new. It is one of the oldest findings in educational measurement.

**Feature-based analysis of writing (1966 to present).** Ellis Page's Project Essay Grade introduced the distinction between *trins* (the intrinsic qualities we care about, such as fluency and organisation) and *proxes* (measurable proxies for them, such as sentence length and vocabulary range). Page demonstrated that proxes correlate strongly with human judgments. Every subsequent system, including ETS's e-rater (Attali and Burstein, 2006), builds on this finding. The Coh-Metrix research programme (Graesser et al., 2004; McNamara, Crossley and McCarthy, 2010) established in detail which linguistic indices predict expert ratings of writing quality, with indices of language sophistication such as lexical diversity and syntactic complexity among the strongest predictors.

**Writing analytics and human sense-making.** More recent work reframes these measures as support for human interpretation rather than inputs to automated scores. AcaWriter, developed at the University of Technology Sydney (Knight et al., 2020), highlights rhetorical signals in student writing for humans to act on. This tradition, learning analytics as augmentation of human judgment rather than replacement of it, is the direct ancestor of the signal-based approach.

**Automated assessment of code.** Programming education has used automated analysis for decades (Ala-Mutka, 2005; Paiva, Leal and Figueira, 2022). Complexity metrics (McCabe, 1976), style analysis, and test coverage are mature, well-understood signals, and using static analysis to inform rather than replace marker judgment is established practice in computing education.

**Multimodal learning analytics.** For artefacts beyond text and code, the multimodal learning analytics field (Blikstein and Worsley, 2016) demonstrates automated extraction of meaningful signals from video, audio, and presentation artefacts, including delivery measures such as pacing and structure.

Taken together: the signals themselves are validated by decades of research, and the decision to route them to a human rather than a scoring model follows the strongest current thinking in learning analytics.

## Why not just automate the scoring?

Because the research is equally clear about the limits of full automation, and the tool is designed around three of them.

**Construct under-representation.** Surface measures capture part of what makes work good, never all of it (Deane, 2013). Argument quality, originality, appropriateness to audience, and disciplinary judgment resist reduction to countable properties. An automated score silently substitutes the measurable for the valuable. A human reading signals in context does not.

**Gaming.** Any fixed formula over surface features can be reverse-engineered. Work by Les Perelman and others demonstrated that automated essay scorers reward long, vocabulary-dense nonsense. A formula cannot notice that a submission is optimised for the metric rather than the criterion. A marker can, and the signals often make the gaming *more* visible, not less.

**Accountability and validity.** Established frameworks for the responsible use of automated scoring (Williamson, Xi and Breyer, 2012) and argument-based validity (Kane, 2013) require that every claim a score supports be backed by an explicit chain of warrants. Keeping a human in the judgment seat keeps that chain short, inspectable, and defensible. It is worth noting that even the most experienced operators of automated scoring, such as ETS, have historically deployed machine scores as a check alongside human raters rather than a replacement for them (Zhang, 2013).

## What the tool explicitly does not do

To be trusted, a tool should state its limits as clearly as its capabilities.

- It does not assign marks, grades, or scores. The mark of record is always entered by a person. Where an interface offers a mark *estimate*, it is a transparent weighting of the signals through the rubric mapping — inspectable down to the contributing values, hidden by default precisely so it cannot anchor the marker, and never recorded as the mark.
- It does not rank students. Cohort context shows where a submission sits in the distribution of signals — unusually similar, unusually distinctive — as a neutral prompt to look closer, never as a league table or a verdict.
- It does not adapt its output based on previous marks. A marking session may record the marker's agreement with each signal for audit and calibration research, but nothing feeds back into what the tool shows for the next submission.
- It does not claim the signals are complete. They are evidence, not the whole of the evidence. The marker's own reading of the work remains primary.

## The marker's role

The tool changes what markers spend their time on, not what they are responsible for. Every mark remains a human judgment, made by a marker who has engaged with the student's work, informed by systematically gathered evidence rather than replaced by it.

In practice, markers report that the signals function like a colleague's pre-reading notes: they orient attention, surface things worth a closer look, and provide consistent reference points across a large cohort. They do not, and cannot, decide anything.

The goal is a marking process that is faster because the mechanical work is automated, more consistent because every artefact is observed the same way, and more defensible because the evidence behind each judgment is explicit. What it is not, and will not become, is automated grading.

## References

Ala-Mutka, K. (2005). A survey of automated assessment approaches for programming assignments. *Computer Science Education*, 15(2), 83-102.

Attali, Y., & Burstein, J. (2006). Automated essay scoring with e-rater v.2. *Journal of Technology, Learning, and Assessment*, 4(3).

Blikstein, P., & Worsley, M. (2016). Multimodal learning analytics and education data mining: Using computational technologies to measure complex learning tasks. *Journal of Learning Analytics*, 3(2), 220-238.

Deane, P. (2013). On the relation between automated essay scoring and modern views of the writing construct. *Assessing Writing*, 18(1), 7-24.

Graesser, A. C., McNamara, D. S., Louwerse, M. M., & Cai, Z. (2004). Coh-Metrix: Analysis of text on cohesion and language. *Behavior Research Methods, Instruments, & Computers*, 36(2), 193-202.

Kane, M. T. (2013). Validating the interpretations and uses of test scores. *Journal of Educational Measurement*, 50(1), 1-73.

Knight, S., Shibani, A., Abel, S., Gibson, A., Ryan, P., Sutton, N., Wight, R., Lucas, C., Sandor, A., Kitto, K., Liu, M., Vijay Mogarkar, R., & Buckingham Shum, S. (2020). AcaWriter: A learning analytics tool for formative feedback on academic writing. *Journal of Writing Research*, 12(1), 141-186.

McCabe, T. J. (1976). A complexity measure. *IEEE Transactions on Software Engineering*, SE-2(4), 308-320.

McNamara, D. S., Crossley, S. A., & McCarthy, P. M. (2010). Linguistic features of writing quality. *Written Communication*, 27(1), 57-86.

Mislevy, R. J., Steinberg, L. S., & Almond, R. G. (2003). On the structure of educational assessments. *Measurement: Interdisciplinary Research and Perspectives*, 1(1), 3-62.

Page, E. B. (1966). The imminence of grading essays by computer. *Phi Delta Kappan*, 47(5), 238-243.

Paiva, J. C., Leal, J. P., & Figueira, A. (2022). Automated assessment in computer science education: A state-of-the-art review. *ACM Transactions on Computing Education*, 22(3), 1-40.

Williamson, D. M., Xi, X., & Breyer, F. J. (2012). A framework for evaluation and use of automated scoring. *Educational Measurement: Issues and Practice*, 31(1), 2-13.

Zhang, M. (2013). Contrasting automated and human scoring of essays. *R&D Connections*, 21, 1-11. Educational Testing Service.
