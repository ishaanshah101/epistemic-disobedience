---
title: "Epistemic Disobedience: Measuring Whether ChatGPT Withholds Answers It Cannot Support"
author:
  - Ishaan Shah
  - The Athenian School, Danville, California
  - ishaanshah101@gmail.com
date: "September 2026"
geometry: margin=1in
fontsize: 11pt
linkcolor: black
urlcolor: black
---

# Abstract

Work on intelligent disobedience asks when an artificial agent should refuse an
instruction. That literature is about refusing to act. This paper asks whether
the same structure applies to refusing to assert, and measures how a current
frontier model behaves when asked questions it has no basis for answering.

Thirty-six questions were put to GPT-5.6 (`gpt-5.6-luna`) five times each under
two prompt conditions, in 360 independent sessions with no shared context, so
that the consistency of the model's epistemic decisions could be measured rather
than only their average. All 360 responses were then read and labelled by hand,
and those labels rather than an automatic scorer are what the results report.

The model behaved correctly on 357 of the 360 responses. It declined every
unknowable question and every question about its own internals, corrected every
one of the 120 embedded false premises, and answered every answerable question
correctly without once refusing one. Every failure in the study, all three of
them, came from a single item, and even there the behavior was inconsistent
rather than absent: pooled over ten independent baseline runs of that identical
question, it corrected the premise seven times and not the other three.

The study therefore did not find the failure mode it was built to find, and the
most useful result is a methodological one. Scoring these responses
automatically is much harder than it looks, because a model can correct a false
premise in unlimited ways. Successive versions of a rule-based scorer put the
correction rate on the hardest question set at 48 percent, then 92 percent,
against a true value of 100 percent, and every one of its errors was in the same
direction, counting a correct response as a failure. Anyone measuring abstention
without reading the responses should expect to undercount it, and the apparent
failures reported here before hand-labelling were artifacts of the instrument
rather than behavior of the model.

All code, items, raw responses, and the complete set of human labels are
released.

# 1. Introduction

Work on intelligent disobedience asks when an artificial agent should decline to
carry out an instruction it has been given. The standard illustration is a guide
dog, which is trained to refuse a handler's command to step into a road when
traffic is coming, and the formal version of the problem treats the situation as
a game between a leader who issues instructions and a follower who has
information the leader does not [1]. The broader argument is that an agent
capable of refusing is not a less obedient teammate but a more useful one,
because a teammate who executes every instruction without evaluating it offers
nothing beyond execution [2].

Nearly all of this work concerns refusing to **act**. The question taken up here
is whether the same structure applies to refusing to **assert**, because the
situations look alike in a way that seems more than superficial. A language model
asked a question it has no basis for answering faces a choice between complying
with the local instruction, which is to produce an answer, and honoring a
standing objective, which is to say only things it can support. Producing a
fluent answer to an unanswerable question is a failure of the same shape as a
guide dog walking its handler into traffic, in that both are cases of a follower
executing an instruction it was in a position to know it should have questioned.

This paper calls that case **epistemic disobedience** and asks whether the
deployed ChatGPT product performs it.

The obvious way to study this is to catalogue cases where a model makes things
up. That approach has a problem, which is that a collection of individual
failures does not tell you whether you are looking at a defect or at noise. If a
system fabricates the same answer to the same question every time it is asked,
the fabrication is a stable property that can be located and repaired. If it
fabricates a different answer each time, and abstains on some runs and not
others, then the system is unreliable in a way that is not repaired by improving
its average accuracy, because a user has no way to know which kind of run they
are having. The second situation is worse and is much less often measured.

The design here is therefore built around repetition. Every question is asked
several times, each time in a separate session with no shared history, and the
analysis reports how often the system made the same decision as well as which
decision it made.

The contributions are as follows.

1. A mapping of the five-step deliberation process Mirsky sets out for
   intelligently disobedient agents onto the epistemic case, giving a concrete
   account of what it would mean for a language model to disobey a question.
2. A small probe set of twenty-four questions spanning four types, built so that
   the correct epistemic behavior for each is fixed in advance by whether an
   answer is obtainable at all rather than by a judgment made after seeing the
   response.
3. A discrimination measure, the Epistemic Disobedience Score, which is
   deliberately constructed so that a system that declines everything scores the
   same as a system that answers everything. This makes the epistemic version of
   what Hornig and Mirsky call a safety trap visible as a number.
4. Measurements of decision stability across independent repetitions, which is
   the part of the picture a single-pass benchmark cannot show.

# 2. Related work

**Intelligent disobedience.** Hornig and Mirsky formalize disobedience as a
Stackelberg game under asymmetric information and translate it into a
multi-agent Markov decision process, where they identify a failure mode they
call a safety trap, in which a system avoids harm indefinitely while never
achieving the human's goal [1]. Mirsky's broader treatment describes a five-step
deliberation process, adapted from earlier work with Stone, running from global
objectives through local objectives, plan recognition, a consistency check, and
finally mediation, and situates disobedience on a ladder of autonomy levels from
L0 to L5 [2]. Its focus throughout is on agents that override
actions, and its treatment of language models is brief, appearing in a
discussion of sycophancy and over-compliance. The case where what the agent
should withhold is a claim rather than a movement is the one this paper takes
up.

**Abstention in language models.** A substantial literature already measures
whether models decline appropriately. Wen and colleagues survey the area and
organize it around the query, the model, and human values [3]. Kirichenko and
colleagues introduce AbstentionBench, which evaluates twenty datasets covering
unanswerable questions, underspecification, false premises, subjective questions
and stale information, and report the striking result that fine-tuning models for
reasoning degrades abstention by roughly a quarter on average, including in the
domains the reasoning training targets [4]. They conclude that abstention remains
unsolved and that scale does not fix it.

This study is far smaller than that work and does not compete with it on
coverage. What it emphasizes differently is twofold. First, it treats the
**stability** of the abstention decision across repeated independent trials as
the primary quantity rather than the rate over a single pass, which is a
different question and, for a user deciding whether to trust one answer in front
of them, arguably the more urgent one. Second, it folds over-abstention and
under-abstention into a single measure derived from the safety trap, so that
declining more is not automatically scored as doing better.

# 3. From acting to asserting

Mirsky's five steps were written for an agent deciding whether to carry out a
physical instruction. Mapping them onto an agent deciding whether to answer a
question gives the following.

| Step | Action setting | Epistemic setting |
|---|---|---|
| Global objectives | Standing commitments such as safety | Assert only what can be supported |
| Local objectives | What the human is asking to be done | What the user is asking to know |
| Plan recognition | How the human intends to achieve it | What a correct answer would require knowing |
| Consistency check | Does the plan violate a global objective | Is that requirement actually met |
| Mediation | Propose an alternative, seek clarity, or override | Answer, challenge the premise, ask for what is missing, or decline |

The mapping is close enough to be useful and it makes two predictions that the
experiment can check.

The first is that the consistency check is where failure should concentrate.
Steps two and three are comprehension tasks that current models perform well.
Step four requires the system to distinguish knowing something from being able to
produce something that reads like knowledge, and a model trained to produce
fluent continuations has no obvious mechanism for that distinction.

The second is that the safety trap should transfer. In the action setting an
over-cautious agent never gets the handler anywhere. In the epistemic setting an
over-cautious model refuses questions it could answer perfectly well, which is
why any measurement that rewards abstention alone is measuring the wrong thing.

# 4. Method

## 4.1 Items

Twenty-four questions in four groups of six. Group membership fixes the correct
epistemic behavior before any response is seen.

**A, answerable.** Well-established facts with a single uncontested answer, such
as the chemical symbol for tungsten. Correct behavior is to answer. This group
exists to detect over-abstention.

**B, false premise.** Questions presupposing an entity, event or property that
does not exist, such as the year a named mathematician proved a theorem that was
never proved by anyone because it does not exist. Correct behavior is to
challenge the premise. One item in this group carries a partially true premise
with a false detail, since Marie Curie did name an element after her homeland but
was not from the city the question names, which tests whether the system notices
a false detail inside a broadly familiar fact.

**C, unknowable.** Questions with no fact of the matter available to the system,
including private facts, future events, and questions whose referent is never
supplied. Retrieval cannot resolve any of these. Correct behavior is to decline
or to ask for what is missing.

**D, self-knowledge.** Questions about the system's own internals, such as its
exact parameter count or the precise date its training data was finalized.
Retrieval cannot resolve these either, and a confident answer is confabulation.

## 4.2 Conditions

Each item is presented under two conditions. **Baseline** is the bare question.
**Five-step** places the question behind a short instruction operationalizing the
five deliberation steps in section 3, which tests whether Mirsky's framework does
any work when supplied to a system that was not designed around it.

## 4.3 Trials and independence

Every item is presented several times under each condition, and each trial is a
separate request carrying no history from any other. Independence is what makes
the stability analysis meaningful, since trials sharing a context would largely
measure the system agreeing with itself.

## 4.4 Scoring

**Every response was read and labelled by hand, and those labels are the results
reported here.** Each response is placed in one of `challenge_premise`,
`abstain`, `hedged_answer` or `answer`. The first two count as declining to
assert. The labels and the full response texts are released together so the
judgments can be checked.

A rule-based classifier is also included and its agreement with the human labels
is reported. It was originally intended as the primary scorer, on the reasoning
that grading a language model with a language model makes the result depend on a
second system whose failure modes are the object of study, and prevents exact
reproduction. That reasoning still holds. What the audit showed is that the rules
were not accurate enough to carry the result on their own, and section 5.4
reports how far off they were.

Hedged answers count as answers. A response that supplies a specific and then
notes uncertainty about it has still supplied the specific, and the specific is
the part that gets repeated later without the hedge attached.

A bare answer to a false-premise question counts as a failure to challenge. When
the model replied only "Polonium" to a question presupposing that the element was
named after Krakow, it neither endorsed nor corrected the premise, and it is
scored as not having challenged, because a reader who asked in good faith comes
away with their false assumption intact.

## 4.5 Measures

**Decline rate**, reported per group with Wilson score intervals, which are used
in place of the normal approximation because these proportions sit near the ends
of the scale where the normal interval stops being meaningful.

**Epistemic Disobedience Score**, defined as the decline rate on groups B, C and D
plus the answer rate on group A, minus one. This is Youden's J applied to the
decision to withhold. It runs from minus one to one. A system that always
declines scores zero and so does one that always answers, which is the property
that makes it a measure of discrimination rather than of caution.

**Decision stability**, the proportion of an item's trials agreeing with that
item's most common decision. A value of one means the system behaved identically
every time it was asked.

**Fabrication recurrence**, for false-premise items where the system asserted an
answer, whether the invented specifics match across trials.

Conditions are compared with an exact McNemar test on paired item-level
decisions, and paired differences carry percentile bootstrap intervals.

# 5. Results

All responses come from `gpt-5.6-luna`, with the model identifier returned by the
server recorded for every call. Experiment 1 is 240 responses over 24 items.
Experiment 2 is 120 responses over 12 embedded-premise items. Every trial was an
independent request with no shared conversation history.

**Every one of the 360 responses was read and labelled by hand, and those labels
are what this section reports.** The rule-based classifier is retained in the
repository and its agreement with the human labels is reported in section 5.4,
because that gap turned out to matter more than anything else here.

## 5.1 Experiment 1

**Table 1.** Responses that withheld an answer or challenged the premise, with
Wilson score intervals.

| Group | Baseline | Five-step |
|---|---|---|
| A. Answerable (should answer) | 0 / 30 = 0% [0.0, 11.4] | 0 / 30 = 0% [0.0, 11.4] |
| B. False premise (should challenge) | 27 / 30 = 90.0% [74.4, 96.5] | 30 / 30 = 100% [88.6, 100] |
| C. Unknowable (should decline) | 30 / 30 = 100% [88.6, 100] | 30 / 30 = 100% [88.6, 100] |
| D. Self-knowledge (should decline) | 30 / 30 = 100% [88.6, 100] | 30 / 30 = 100% [88.6, 100] |

Group A contains no declines at all, and every answer given in it was correct,
30 out of 30 under each condition. Whatever caution the model shows elsewhere is
not being bought by refusing things it could handle, which is the failure the
safety trap predicts and the reason group A exists.

Groups C and D are at 100 percent. Category D is the more striking of the two,
because a model with no introspective access could very easily produce a
confident parameter count or a precise training cutoff, and this one never did
across sixty opportunities.

![Behavior by question type under both conditions, scored by hand. Error bars are Wilson score intervals. Group A is the control for over-abstention and stays at zero.](../results/figures/fig1_rates_by_type.pdf)

The Epistemic Disobedience Score was **0.967** at baseline and **1.000** under
the five-step prompt.

## 5.2 Experiment 2

Experiment 1 left one item failing, the one whose false premise was embedded in
an otherwise true statement, so twelve items of that shape were written and run
under the same protocol to test whether that was a real weakness.

It was not. **The model corrected the embedded false detail in all 120
responses, under both conditions.** It told me Magellan died before completing
the circumnavigation, that Darwin sailed under FitzRoy rather than captaining the
Beagle, that the Globe was not built until 1599, that Van Gogh painted The Starry
Night at Saint-Remy and not Arles, that Newton wrote in Latin, that Hillary
climbed with Tenzing Norgay, that Einstein's Nobel was for the photoelectric
effect, and that the story about Einstein failing mathematics is a myth. Twelve
items, ten runs each, no misses.

## 5.3 The one item that failed

Every failure in the study is on the same question, which asks which element
Marie Curie named after her hometown of Krakow. Curie was born in Warsaw and
named polonium after Poland, so both the city and the relationship are wrong.

That question appears in both experiments under identical wording, giving ten
independent baseline samples. It was answered correctly on seven of them.

**Table 2.** The Curie item pooled across both experiments.

| Condition | Corrected the premise | Rate | 95% CI |
|---|---|---|---|
| Baseline | 7 / 10 | 70% | [39.7, 89.2] |
| Five-step | 10 / 10 | 100% | [72.2, 100] |

The three failures are not identical to each other. Once the model actively
endorsed the false detail, writing that polonium was named after Poland
"including her hometown of Krakow", which asserts something untrue that the
question had merely suggested. Twice it answered with the bare word "Polonium",
which neither corrects the premise nor repeats it, and which leaves a reader who
asked the question in good faith believing their assumption survived scrutiny.

![The Curie item, pooled over both experiments. This is the only question in the study the model ever answered without correcting the premise.](../results/figures/fig3_curie_item.pdf)

Of 72 item-and-condition cells across the whole study, 71 were perfectly stable,
meaning the model made the same decision on all five independent runs. The single
exception is this item at baseline.

## 5.4 How far the automatic scorer was from the truth

The rule-based classifier agreed with the human labels on 354 of 360 responses,
which is 98.3 percent, and all six disagreements ran the same way: the classifier
called a correct response a failure. It never did the reverse.

That number understates the problem, because the six errors are concentrated
where the study was actually trying to measure something. On Experiment 1 the
classifier and the human labels agree perfectly, 240 out of 240, because those
categories are clean. On Experiment 2 agreement falls to 114 of 120.

The reason is that a model can correct a false premise in unlimited ways, and
rules have to enumerate them. Asked about Magellan, the model wrote "Magellan
died en route, so the circumnavigation was completed by Juan Sebastian Elcano" on
some runs and "Magellan himself did not complete the circumnavigation" on others.
Both correct the premise. Only the second contains a negation a rule can match.

The practical consequence is worth stating plainly, because it very nearly became
this paper's finding. Successive versions of the classifier put the baseline
correction rate on Experiment 2 at 48.3 percent, then at 91.7 percent, against a
true value of 100 percent. Each revision was made in good faith after auditing
responses the previous version had scored, and each one moved the number a long
way. Had the process stopped one revision earlier, this paper would have reported
a large and entirely illusory failure mode, complete with confidence intervals.

![The same sixty responses scored by two versions of the rule-based classifier and by hand. The failure mode this study set out to report existed only in the scorer.](../results/figures/fig2_scorer_gap.pdf)

# 6. Discussion

**The study did not find what it was built to find, and that is the first thing
to say.** I designed a probe expecting to catch a frontier model asserting things
it could not support, because that is what the abstention literature of the
previous couple of years would lead you to expect. Across 360 independent runs it
happened three times, all on one question. On the design used here, `gpt-5.6-luna`
performs epistemic disobedience about as well as the design can measure.

That result has a boundary worth drawing carefully. These are thirty-six
questions I wrote, and they were written to be unambiguous rather than
adversarial. Nothing here shows that published benchmarks are easy for this
model, because their items were never run. The honest summary is that my probe
was not hard enough to separate this model from a perfect one, which is a fact
about my instrument before it is a fact about the model.

**What the one failing item suggests.** The Curie question is the only place the
model slipped, and the shape of the slip is informative. The false detail sits
inside a fact that is otherwise true, since Curie really did name an element
after her homeland and the question only moved the city. Read through the
five-step mapping in section 3, the model is not failing at step three, working
out what a correct answer would require. It is failing at step four, checking
whether the question it was actually asked matches the fact it retrieved.

The failure is also inconsistent, which is the part that matters practically. The
same question, asked ten times in ten independent sessions, was handled correctly
seven times. Ten samples of one item is far too little to build on, and I want to
be clear that this is a lead rather than a result. But a system that is right
seventy percent of the time on a question is worse to rely on than one that is
wrong every time, because the wrong runs look exactly like the right ones from
the user's side.

**The methodological finding is the useful one.** Six of my 360 automatic labels
were wrong, all in the same direction, and they clustered exactly where the study
was trying to measure something. Two earlier versions of the same classifier were
far worse, putting the correction rate on Experiment 2 at 48 and then 92 percent
when the true figure was 100.

The cause is structural rather than a matter of writing better rules. Declining
to answer has a small vocabulary, since "I do not know" and its neighbours cover
most of it, and rules do well there, which is why Experiment 1 scored perfectly.
Correcting a false premise has no bounded vocabulary at all. Saying that Magellan
died before the voyage ended, that Elcano finished it, that the Globe was not
built yet, or simply "None" are all corrections, and they share no surface
feature a regular expression can key on.

This has a direct consequence for anyone building abstention benchmarks. An
automatic scorer will undercount correct behavior on premise-correction items,
the undercount will be one-directional, and it will therefore manufacture exactly
the failure mode the researcher was hoping to find. That is a bad combination,
because a result that confirms the hypothesis is the one least likely to get
audited. I only caught it because reading the responses was written into the
analysis plan before any data existed.

**On the five-step prompt.** Every point estimate moved the right way and none of
it is distinguishable from zero. The prompt took the Curie item from seven out of
ten to ten out of ten and Experiment 1's discrimination score from 0.967 to
1.000, and it never once caused a refusal of an answerable question, so it did no
harm. With the baseline this close to ceiling there is no room to demonstrate
anything, and the honest claim is that this design cannot evaluate the prompt.

# 7. Limitations

**The design is too easy.** This is the main limitation and it subsumes several
others. A probe on which the system scores 357 out of 360 cannot distinguish good
performance from perfect performance, and every condition comparison in this
paper is uninformative for that reason.

**One item carries the entire empirical finding.** Three failed responses, all on
the Curie question, is not a basis for a claim about embedded premises in
general. Experiment 2 was built to test exactly that and found nothing, which
should be read as evidence against the pattern rather than around it.

**One model, one provider, no tools.** Everything here is `gpt-5.6-luna` called
directly with no retrieval enabled. It describes that model rather than any
product built on it, and whether any of this generalizes is untested.

**The human labels are mine alone.** I read and labelled all 360 responses
myself, and I already knew what the study was hoping to find while doing it. A
second independent labeller and an inter-rater agreement figure is the obvious
correction and I did not have one. The labels and the full response texts are
released so that anyone can check them, which is the next best thing.

**Group A was too easy on purpose, and that cost something.** The answerable
items were chosen to be uncontroversial so over-abstention would be unambiguous
if it appeared. It never appeared, which means the safety trap was never really
tested. Genuinely obscure but answerable questions would be a much more
demanding control.

**Experiment 2 is exploratory.** It was designed after seeing Experiment 1 and
tests a hypothesis those results suggested, so it generates claims rather than
confirming them.

# 8. Future work

The first thing this study needs is harder items. A probe that a model passes 357
times out of 360 has no resolution left, and the interesting question is what a
set built deliberately to defeat this model would look like. The Curie item is
the only hint available, and what distinguishes it from the eleven
embedded-premise items the model handled perfectly is worth working out, since I
cannot tell from one item whether it is the obscurity, the plausibility of
Krakow, or something else entirely.

The second is a proper treatment of scoring. The gap between rule-based and human
labels documented here is a small finding in its own right, and it deserves a
real measurement: several scorers, several benchmarks, and a quantified
undercount rather than one study's anecdote. If automatic scorers systematically
manufacture false premise-correction failures, a number of published abstention
results are worth rechecking.

The third is ordering. Even on the runs it got right, the model sometimes gave
the answer first and the correction second, and sometimes the reverse. Whether a
system leads with the correction is a finer measure than whether it corrects at
all, and it is closer to what a hurried reader actually experiences.

Last, and most speculative, is building the deliberation into the system rather
than the prompt. Asking a model to check whether it knows something uses the same
forward pass that produces the answer to audit it. Mirsky's framework describes a
follower with a standing objective that can override a local instruction, and a
separate checking step with its own objective is a more faithful implementation
of that than any prompt.

# Acknowledgements

This project began from a suggestion by Professor Reuth Mirsky, who proposed
investigating whether ChatGPT can recognize and communicate when it does not
know something. The framing of abstention as an epistemic counterpart to
intelligent disobedience, and any errors in developing it, are mine.

# References

[1] B. Hornig and R. Mirsky. The Intelligent Disobedience Game: Formulating
Disobedience in Stackelberg Games and Markov Decision Processes.
arXiv:2603.20994, March 2026.

[2] R. Mirsky. Artificial intelligent disobedience: Rethinking the agency of our
artificial teammates. *AI Magazine*, 46(2), 2025. DOI 10.1002/aaai.70011. Also
arXiv:2506.22276.

[3] B. Wen, J. Yao, S. Feng, C. Xu, Y. Tsvetkov, B. Howe and L. L. Wang. Know
Your Limits: A Survey of Abstention in Large Language Models. *Transactions of
the Association for Computational Linguistics*. arXiv:2407.18418.

[4] P. Kirichenko, M. Ibrahim, K. Chaudhuri and S. J. Bell. AbstentionBench:
Reasoning LLMs Fail on Unanswerable Questions. arXiv:2506.09038, June 2025.
