"""
Generates a DEMO dataset (data/train_data.csv) with far more lexical and
structural diversity than a handful of fixed templates, plus deliberate
"hard" examples (formal human writing, casual AI filler) so the model can't
shortcut to "contains the word furthermore = AI".

STILL only a synthetic demo. For real-world reliability, replace this with a
real public dataset (see README section on real datasets) via:
    python train_model.py --csv your_real_dataset.csv
"""
import os
import random
import pandas as pd

random.seed(7)

topics = [
    "artificial intelligence", "renewable energy", "social media", "remote work",
    "online education", "climate change", "electric vehicles", "genetic engineering",
    "cryptocurrency", "space exploration", "virtual reality", "machine learning",
    "urban planning", "mental health awareness", "the gig economy", "5G networks",
    "biodiversity loss", "self-driving cars", "quantum computing", "public transportation",
    "influencer marketing", "vaccine development", "3D printing", "smart home devices",
]
fields = [
    "education", "healthcare", "business", "communication", "science",
    "the economy", "daily life", "research", "society", "the workplace",
    "urban development", "agriculture", "the entertainment industry", "government policy",
]
verbs = ["learn", "communicate", "work", "study", "interact", "collaborate", "shop", "travel"]

# ---------------- AI-style building blocks (formal / structured) ----------------
ai_openers = [
    "{Topic} has fundamentally reshaped how people approach {field}.",
    "The emergence of {topic} has introduced new possibilities within {field}.",
    "In recent years, {topic} has become increasingly central to {field}.",
    "Advancements in {topic} continue to influence {field} in measurable ways.",
    "{Topic} represents one of the most discussed developments affecting {field} today.",
]
ai_middles = [
    "This shift has enabled organizations to {verb} more efficiently than before.",
    "As a result, professionals in {field} have had to adapt their traditional methods.",
    "Numerous studies have highlighted both the benefits and challenges associated with this trend.",
    "Stakeholders across {field} have expressed a range of perspectives on this development.",
    "The scale of this change has prompted renewed interest from researchers and policymakers alike.",
    "It is worth noting that adoption rates vary considerably across different regions.",
]
ai_transitions = ["Furthermore,", "Moreover,", "Additionally,", "As such,", "Notably,", "Consequently,"]
ai_closers = [
    "Overall, the long-term implications of {topic} for {field} remain an important area of study.",
    "In conclusion, {topic} is likely to remain a defining factor in {field} for years to come.",
    "Ultimately, the relationship between {topic} and {field} will continue to evolve.",
    "In summary, the impact of {topic} on {field} cannot be overstated.",
]
# hard positives: AI text trying to sound casual, but still generic/filler
ai_casual_fillers = [
    "So basically, {topic} is changing things in {field}, which is pretty interesting to think about.",
    "It's kind of amazing how {topic} keeps coming up whenever people talk about {field} these days.",
    "You could say {topic} is one of those things that's quietly transforming {field} in a big way.",
    "A lot of people are talking about {topic} lately, especially in relation to {field}.",
]

# ---------------- Human-style building blocks (casual / personal / uneven) ----------------
human_openers = [
    "Yesterday I was thinking about {topic} and honestly it kind of confused me at first.",
    "My friend brought up {topic} at dinner and we ended up arguing about {field} for like an hour.",
    "I don't know much about {topic}, but my cousin works in {field} and never stops talking about it.",
    "So I tried using {topic} for a {field} project last week and it was messier than I expected.",
    "Not gonna lie, {topic} still feels kind of new to me even though everyone talks about {field} now.",
    "Reading about {topic} on the bus this morning, I nearly missed my stop.",
    "My professor mentioned {topic} in class today and I mostly zoned out thinking about lunch.",
    "Honestly {topic} is kind of overrated imo, especially when it comes to {field}.",
]
human_asides = [
    "Anyway,", "Like I said,", "But yeah,", "Still,", "I mean,", "To be fair,", "Honestly though,",
]
human_middles = [
    "it's just weird how fast things change in {field} sometimes.",
    "I guess it makes sense given everything going on in {field} lately.",
    "nobody really explained it to me properly, so I'm just guessing here.",
    "my roommate thinks it's overhyped, but what does she know.",
    "I've heard mixed things about how it's affecting {field}.",
    "it's not like {field} was perfect before anyway.",
]
human_closers = [
    "Not sure what I actually think about it yet.",
    "Guess we'll see how it plays out.",
    "Either way, it's been on my mind a lot lately.",
    "I'll probably look into it more this weekend.",
    "",  # sometimes no closer at all, human writing just trails off
]
# hard negatives: human writing that's more formal (e.g. an essay) but still has a personal touch
human_formal = [
    "I think {topic} has genuinely changed {field}, though I'm still not sure it's all for the better.",
    "In my experience, {topic} has made {field} more efficient, but it's also created new problems nobody talks about.",
    "From what I've seen working in {field}, {topic} is useful, though people overestimate how much it actually helps day to day.",
    "I've read a lot about {topic} and {field}, and honestly the research feels more mixed than most headlines suggest.",
]


def fill(t):
    return t.format(topic=random.choice(topics), Topic=random.choice(topics).capitalize(),
                     field=random.choice(fields), verb=random.choice(verbs))


def make_ai_text():
    if random.random() < 0.15:  # hard positive: casual-sounding AI filler
        n = random.randint(2, 3)
        return " ".join(fill(random.choice(ai_casual_fillers)) for _ in range(n))
    parts = [fill(random.choice(ai_openers))]
    n_middle = random.randint(1, 3)
    for _ in range(n_middle):
        sent = fill(random.choice(ai_middles))
        if random.random() < 0.5:
            sent = f"{random.choice(ai_transitions)} {sent[0].lower() + sent[1:]}"
        parts.append(sent)
    parts.append(fill(random.choice(ai_closers)))
    return " ".join(parts)


def make_human_text():
    if random.random() < 0.15:  # hard negative: more formal human writing
        n = random.randint(1, 2)
        return " ".join(fill(random.choice(human_formal)) for _ in range(n))
    parts = [fill(random.choice(human_openers))]
    n_middle = random.randint(0, 3)
    for _ in range(n_middle):
        sent = fill(random.choice(human_middles))
        if random.random() < 0.6:
            sent = f"{random.choice(human_asides)} {sent}"
        parts.append(sent.capitalize())
    closer = random.choice(human_closers)
    if closer:
        parts.append(closer)
    return " ".join(parts)


N_PER_CLASS = 1500
rows = []
for _ in range(N_PER_CLASS):
    rows.append({"text": make_ai_text(), "label": 1})
for _ in range(N_PER_CLASS):
    rows.append({"text": make_human_text(), "label": 0})

df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
df = df[df["text"].str.split().str.len() >= 5]

out_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "train_data.csv")
df.to_csv(out_path, index=False)
print(f"Wrote {len(df)} rows to {out_path}")
