"""The Digital Slang Archive, Session 3: slang community by community, as Luma reads it.

Built from the owner's research archive (scripts/build_slang_archive.py turns the .docx into this file). Same line format
as slang_data.LEXICON; where a word is already in slang_data, Luma keeps that meaning and learns the new spellings and
communities. DETAILS holds where each word comes from, how it's used and an example, for "what does X mean?". EXAMPLES
are the archive's own sentences: they teach the understanding model that talk like this is conversation, not a command.

Slurs aren't in here (the archive leaves them out on purpose). Words aimed at people, or labels for a group, are marked
s: Luma understands and explains them and doesn't say them. EVERYDAY words are ordinary English too ("cool", "house",
"tank"), so seeing one doesn't count as a sign that someone talks in slang.
"""
ORIGINS = {'appalachia': 'Appalachia',
 'northeast': 'the Northeast (Boston, New York, Philly, Pittsburgh, Baltimore)',
 'west': 'the West Coast and the Pacific Northwest',
 'subculture': 'skate, surf, emo and other scenes',
 'mexican': 'Mexican Spanish and Chicano culture',
 'caribe': 'Puerto Rican, Dominican and Cuban Spanish',
 'latam': 'Central and South American Spanish',
 'filipino': 'Filipino and Taglish',
 'seasia': 'Vietnamese, Thai and Hmong',
 'korean': 'Korean and K-culture',
 'anime': 'Japanese and anime fandom',
 'chinese': 'Chinese and the Chinese diaspora',
 'desi': 'South Asian (Desi) English',
 'hawaii': "Hawai'i Pidgin",
 'westindies': 'Trinidad, Barbados, Guyana and Haiti',
 'africa': 'Nigerian Pidgin and West and East Africa',
 'brit': 'British English',
 'irish': 'Irish English',
 'scotwales': 'Scotland and Wales',
 'aus': 'Australia and New Zealand',
 'arab': 'Arab, Muslim and Persian American speech',
 'pasifika': 'Samoan, Tongan and Māori',
 'native': 'Native American communities',
 'yiddish': 'Yiddish and Jewish American English',
 'italian': 'Italian American speech',
 'cajun': 'Louisiana Cajun and Creole',
 'gullah': 'Gullah Geechee'}

LEXICON = r"""
finna |  | aave | c | about to, or planning to do something very soon | 
ain't | aint | aave | c | a general negative form that can replace am not, is not, are not, has not, and have not | 
steady |  | aave | c | an adverb showing that an action continues persistently or without being deterred | 
bout to |  | aave | c | a reduction of about to, often used to signal immediate action | 
ion |  | aave | c | a written reduction of I don't, as in "Ion know" | 
bet |  | aave | c | okay, agreed, or you're on, used as a quick agreement | 
cap |  | aave | c | a lie or exaggeration | 
no cap |  | aave | c | not lying, used to show sincerity | 
lit |  | aave | c | excellent, exciting, or full of energy | 
slaps |  | aave | c | music or food that is excellent | 
fire |  | aave | c | excellent or impressive | 
drip |  | aave | c | stylish clothing, jewelry, or overall swagger | 
bae |  | aave | c | a term of endearment for a romantic partner | 
salty |  | aave | c | upset, bitter, or irritated, usually over something small | 
extra |  | aave | c | over the top or doing more than needed | 
thirsty |  | aave | c | showing too much eagerness for attention or approval | 
clapback |  | aave | c | a quick, sharp reply to criticism | 
woke |  | aave | c | aware of social injustice, especially racial injustice | 
cuffing season |  | aave | c | the colder months when people seek relationships | 
on god |  | aave | c | a sincere oath that the speaker is telling the truth | 
bussin |  | aave | c | extremely good, usually describing food | 
gang gang |  | aave | c | an affirmation of loyalty or agreement | 
opps |  | aave | c | opponents or enemies | 
tweaking |  | aave | c | acting erratic, overreacting, or behaving in an unreasonable way | 
pressed |  | aave | c | bothered or overly concerned about something | 
boo'd up | bood up | aave | c | in a relationship or spending a lot of time with a partner | 
chile |  | aave | c | an exclamation of disbelief or commentary, spelled child | 
receipts |  | aave | c | proof or evidence, especially screenshots | 
caught in 4k |  | aave | c | caught in the act with undeniable evidence | 
lemme find out |  | aave | c | a playful warning or accusation about a suspected action, as in "Lemme find out you skipped practice" | 
i'm weak | im weak | aave | c | I'm laughing so hard I can barely function | 
it's the ___ for me | its the ___ for me | aave | c | a sentence frame that names the specific detail the speaker finds most striking, as in "It's the hat for me" | 
periodt |  | aave | c | an emphatic ending that means the subject is closed | 
gassed |  | aave | c | hyped up or feeling confident, or praising someone excessively | 
gas |  | aave | c | to hype someone up or the excellent quality of something | 
secure the bag |  | aave | c | to obtain money, a job, or a valuable opportunity | 
flex |  | aave | c | to show off or display success | 
pull up |  | aave | c | to arrive or show up somewhere, often unexpectedly | 
swag |  | aave | c | stylish confidence in how someone looks or moves | 
dap |  | aave | c | a handshake or greeting gesture of respect | 
word up |  | aave | c | an affirmation meaning that's true or I agree | 
dope |  | aave | c | excellent or impressive | 
def |  | aave | c | excellent, a clipped form of definitive | 
phat |  | aave | c | excellent, attractive, or impressive | 
fly |  | aave | c | stylish and attractive | 
crib |  | aave | c | home or residence | 
bling |  | aave | c | flashy jewelry or ostentatious display of wealth | 
grillz |  | aave | c | decorative metal coverings for the teeth | 
cool |  | aave | c | calm, stylish, or excellent | 
hip |  | aave | c | stylish and aware of the latest trends | 
mad |  | aave | c | very, as in mad cool or mad tired | 
deadass |  | aave | c | seriously or truthfully | 
jawn |  | aave | c | an all-purpose noun that can stand for any person, place, or thing | 
hyphy |  | aave | c | energetic, wild, and excited | 
going dumb |  | aave | c | going wild or acting with intense energy | 
hella |  | aave | c | very or a lot | 
mane |  | aave | c | a regional spelling of man, used as a friendly address | 
slab |  | aave | c | a customized car from Houston car culture, standing for slow, loud, and bangin | 
trill |  | aave | c | a blend of true and real, meaning authentic | 
crunk |  | aave | c | wild, high-energy, and loud | 
turnt |  | aave | c | excited, energetic, or intoxicated | 
trap |  | aave | c | a place associated with illegal drug sales, also a style of hip-hop built on heavy bass and hi-hats | 
bando |  | aave | c | an abandoned house, often used for illegal activity, and later used as a stylish reference | 
screwed | chopped | aave | c | a style of slowed-down, rhythmically cut music | 
go-go | go go | aave | c | a percussion-heavy funk genre from Washington, D.C | 
ratchet |  | aave | c | in its newer popular sense, a label for behavior seen as loud or unruly | 
bougie |  | aave | c | pretending to be upper class or displaying refined taste | 
what it do |  | aave | c | a greeting that means what's going on | 
kick it |  | aave | c | to hang out or relax with someone | 
bruh |  | aave | c | a casual address for a friend, often used as a reaction to something surprising | 
boo |  | aave | c | a term of affection for a partner or close friend | 
hater |  | aave | c | someone who criticizes out of jealousy | 
squad |  | aave | c | a close group of friends | 
homie |  | aave | c | a close friend, especially from the same neighborhood | 
house |  | ballroom | c | a chosen family and competitive team in ballroom, led by a house mother or father | 
mother |  | ballroom | c | the leader of a ballroom house who provides guidance, support, and sometimes housing | 
category |  | ballroom | c | a competition theme at a ball in which participants walk to meet specific criteria | 
realness |  | ballroom | c | the ability to pass convincingly as a particular type of person, such as an executive or a student | 
walking |  | ballroom | c | competing in a ballroom category | 
vogue |  | ballroom | c | a stylized dance form built on posed, angular movement | 
vogue femme |  | ballroom | c | a style of voguing that emphasizes fluid, feminine movement, including hands, catwalk, duckwalk, floor performance, and spins and dips | 
duckwalk |  | ballroom | c | a low squatting walk with the body held in a duck-like position | 
death drop |  | ballroom | c | a dramatic dip in which a dancer falls backward or sideways to the floor in a controlled way | 
serving |  | ballroom | c | performing with polish, confidence, and attitude, often written as serving looks | 
kiki |  | ballroom | c | a social gathering, or a subculture of ballroom aimed at younger LGBTQ people | 
legendary |  | ballroom | c | a high status in ballroom for someone who has built a lasting reputation, with the next level being iconic | 
shade |  | ballroom | c | a subtle insult or disrespect | 
reading |  | ballroom | c | a verbal takedown of someone, often witty and detailed | 
tea |  | ballroom | c | gossip or truth | 
slay |  | ballroom | c | to do something exceptionally well | 
snatched |  | ballroom | c | looking flawless, or having a very defined waist | 
ate |  | ballroom | c | performed exceptionally well, often in the phrase ate and left no crumbs | 
yas |  | ballroom | c | an enthusiastic expression of approval, often stretched as yasss | 
gagging |  | ballroom | c | being so impressed or shocked that you have lost words | 
wig |  | ballroom | c | a reaction to something so impressive that your wig has flown off | 
it's giving | its giving | ballroom | c | a phrase that names the vibe something gives off, as in It's giving luxury | 
sickening |  | ballroom | c | extremely good, said of a look or performance | 
hunty |  | ballroom | c | a playful form of address derived from honey | 
sashay |  | ballroom | c | to walk with confident, swaying movement | 
shantay |  | ballroom | c | a phrase from RuPaul's Drag Race, shantay you stay, meaning you survive the elimination | 
werk |  | ballroom | c | a cheer to tell someone to give an excellent performance | 
purr |  | ballroom | c | a sound of approval, meaning a look is good | 
rizz |  | aave+gaming | c | charisma or skill at attracting a romantic interest | 
fanum tax |  | aave+gaming | c | the playful act of taking a portion of someone else's food | 
gyatt |  | aave+gaming | c | an exclamation of surprise or reaction to someone's physique | 
chat |  | aave+gaming | c | the live comment audience on a stream, also used as a form of address, as in chat, is this real | 
w in chat | w in the chat | aave+gaming | c | a message of approval for a win, where W stands for win | 
l in chat | l in the chat | aave+gaming | c | a message of disapproval for a loss | 
take the l |  | aave+gaming | c | to accept a loss or admit defeat | 
clip it |  | aave+gaming | c | a request to save a short video from a live stream | 
bag |  | aave+gaming | c | money or a valuable opportunity, as in secure the bag | 
mic'd up | micd up | aave+gaming | c | wearing or using a microphone so everything can be heard, often used for streams that capture live reactions | 
lobby |  | aave+gaming | c | the waiting area or group session in an online game before a match begins | 
run it back |  | aave+gaming | c | to play again, or to repeat a match | 
light work |  | aave+gaming | c | something done easily | 
clapped |  | aave+gaming | c | defeated badly | 
cooked |  | aave+gaming | c | in serious trouble or defeated, as in we're cooked | 
cracked |  | aave+gaming | c | extremely skilled | 
sweaty |  | aave+gaming | c | playing with intense competitive focus, usually in a casual setting | 
tryhard |  | aave+gaming | c | someone who tries very hard to win, often seen as taking it too seriously | 
cheese |  | aave+gaming | c | to win using a strategy seen as unfair or too easy, or a cheap exploit | 
salty runback |  | aave+gaming | c | an immediate rematch demanded by a player who lost and is frustrated | 
scrub |  | aave+gaming | c | in fighting game culture, a player who blames outside factors for losing and refuses to improve | 
money match |  | aave+gaming | c | a match in which players bet money on the result | 
pocket |  | aave+gaming | c | a character or strategy a player saves for key moments, also used for a player's secret weapon | 
the park |  | aave+gaming | c | the online social area in NBA 2K where players meet and compete in basketball | 
pro-am | pro am | aave+gaming | c | a competitive team mode in NBA 2K | 
green |  | aave+gaming | c | a perfectly timed shot in NBA 2K, signaled by the green indicator | 
badges |  | aave+gaming | c | special abilities that boost a player's skills in NBA 2K | 
dub |  | aave+gaming | c | a win, from the W letter | 
gg |  | aave+gaming | c | good game, said after a match | 
gg ez | ggez | aave+gaming | c | a taunt meaning the game was easy | 
lag |  | aave+gaming | c | delay between a player's action and its effect in an online game | 
ping |  | aave+gaming | c | the response time between a player and a game server, measured in milliseconds | 
carry |  | aave+gaming | c | to lead a team to victory through strong performance | 
clutch |  | aave+gaming | c | succeeding in a high-pressure moment | 
tilt |  | aave+gaming | c | frustration that leads to poor play | 
mid |  | aave+gaming | c | average or disappointing, often used as an insult | 
y'all | yall | south | c | a second-person plural pronoun, a contraction of you all | 
all y'all | all yall | south | c | a more emphatic form of y'all, referring to every person in a group | 
fixin' to | fixin to | south | c | about to, or getting ready to | 
might could |  | south | c | a double modal that expresses a possibility, as in "I might could help" | 
bless your heart |  | south | c | a phrase that can express sympathy or a polite put-down depending on tone | 
reckon |  | south | c | to think or suppose | 
yonder |  | south | c | over there, at a distance | 
coke |  | south | c | a word for any soft drink, as in "What kind of coke do you want" | 
buggy |  | south | c | a shopping cart | 
holler |  | south | c | a small valley, or to shout | 
dadgum |  | south | c | a mild minced oath used as a milder version of a stronger curse | 
cattywampus |  | south | c | crooked, skewed, or out of alignment | 
supper |  | south | c | the evening meal, with dinner often used for the midday meal in some regions | 
directly |  | south | c | soon, or in a short while | 
carry |  | south | c | to drive or take someone somewhere, as in "I'll carry you to the store" | 
mash |  | south | c | to press, as in mash the button | 
hissy fit |  | south | c | a childish display of anger | 
fit to be tied |  | south | c | extremely angry or agitated | 
sugar |  | south | c | a term of endearment used for anyone, from children to strangers | 
ma'am | maam | south | c | polite forms of address used with yes and no, as in yes ma'am | 
pert near |  | south | c | nearly or almost | 
plumb |  | appalachia | c | completely or entirely, as in plumb tuckered | 
right smart |  | appalachia | c | a considerable amount | 
poke |  | appalachia | c | a paper bag or sack | 
tote |  | appalachia | c | to carry | 
sigogglin |  | appalachia | c | crooked or askew | 
young'uns | younguns | appalachia | c | children | 
fair to middlin' | fair to middlin | appalachia | c | moderately well | 
ope |  | midwest | c | a small exclamation made when bumping into someone or noticing a minor mishap | 
pop |  | midwest | c | a carbonated soft drink | 
uff da |  | midwest | c | an exclamation of surprise, burden, or sympathy | 
hotdish |  | midwest | c | a casserole, usually baked in one dish | 
you betcha |  | midwest | c | an enthusiastic yes | 
dontcha know |  | midwest | c | a tag phrase added to the end of a sentence for friendly emphasis | 
yooper |  | midwest | c | a person from the Upper Peninsula of Michigan | 
bubbler |  | midwest | c | a drinking fountain | 
stop and go light |  | midwest | c | a traffic light | 
the cities |  | midwest | c | a reference to Minneapolis and St. Paul together, the Twin Cities | 
up north |  | midwest | c | a general phrase for a vacation area in the northern part of a state, often with lakes | 
minnesota nice |  | midwest | c | a reputation for politeness and indirectness in Minnesota | 
supper club |  | midwest | c | a casual restaurant with traditions such as relish trays and Friday fish fry | 
wicked |  | northeast | c | very or extremely, as in wicked good | 
packie |  | northeast | c | a liquor store, short for package store | 
frappe |  | northeast | c | a milkshake made with ice cream | 
jimmies |  | northeast | c | sprinkles | 
rotary |  | northeast | c | a traffic circle | 
the t |  | northeast | c | the Boston subway and light rail system | 
bodega |  | northeast | c | a small neighborhood corner store | 
stoop |  | northeast | c | a small porch or set of steps at the entrance to a building | 
on line |  | northeast | c | standing in a queue, as in waiting on line | 
regular coffee |  | northeast | c | coffee with milk and sugar | 
youse |  | northeast | c | a plural form of you | 
jagoff |  | northeast | v | a mild insult for an annoying or foolish person | 
yinz |  | northeast | c | a plural form of you in Pittsburgh dialect | 
nebby |  | northeast | c | nosy | 
n'at |  | northeast | c | and that, added to the end of a list | 
redd up |  | northeast | c | to tidy or clean up | 
gumband |  | northeast | c | a rubber band | 
down the shore |  | northeast | c | traveling to the New Jersey or Delaware beach | 
hon |  | northeast | c | a friendly term of address, especially in Baltimore | 
hoagie |  | northeast | c | a long sandwich on a roll, also called a sub or a grinder in other places | 
gnarly |  | west | c | impressive or intense, whether good or bad | 
stoked |  | west | c | very excited and happy | 
rad |  | west | c | great or impressive | 
the 5 and the 405 | the five and the 405 | west | c | the practice of putting the before freeway numbers in Southern California | 
hecka |  | west | c | very, a variant of hella | 
janky |  | west | c | broken, unreliable, or of poor quality | 
gag me with a spoon |  | west | c | an expression of disgust, popularized in 1980s California Valley speech | 
bogus |  | west | c | fake or unfair | 
shred |  | west | c | to ride a surfboard, skateboard, or snowboard with skill | 
send it |  | west | c | to commit fully to a daring move | 
kook |  | west | c | a beginner who behaves as if they are an expert, especially in surfing | 
grom |  | west | c | a young surfer or skater | 
the mountain is out |  | west | c | out means a Seattle expression noting that Mount Rainier is visible on a clear day | 
seattle freeze |  | west | c | a reputation for reserved friendliness in Seattle | 
dank |  | west | c | excellent or high quality, from an older meaning of damp | 
bro |  | subculture | c | a casual term for a male friend, also a label for a style of male social culture | 
dude |  | subculture | c | a general term of address | 
chad |  | subculture | c | a stereotype of a confident, conventionally attractive man | 
ollie |  | subculture | c | a skateboard trick in which the board leaps into the air without the rider's hands | 
kickflip |  | subculture | c | a skateboard trick in which the board flips along its length | 
bail |  | subculture | c | to abandon a trick or an activity, or to leave | 
emo |  | subculture | c | a music genre and a style of expressive emotion | 
scene kid |  | subculture | c | a young person in an alternative subculture of the 2000s known for bright colors and distinctive hair | 
goth |  | subculture | c | a subculture associated with dark aesthetics and post-punk music | 
normie |  | subculture | c | an ordinary person who does not follow niche culture | 
theater kid |  | subculture | c | a person devoted to school drama, often dramatic and enthusiastic | 
redneck |  | subculture | s | a rural, usually white, working-class person, an old term for sunburned farm laborers | 
good ol' boy | good ol boy | subculture | c | a friendly, rural Southern man who is part of a social network | 
hold my beer |  | subculture | c | a phrase that precedes a risky or foolish act | 
tailgate |  | subculture | c | a social gathering around the back of a vehicle, usually before a sporting event | 
touch grass |  | internet | c | a suggestion that someone go outside and reconnect with real life | 
chronically online |  | internet | c | spending so much time on the internet that one's views are distorted | 
doomscrolling |  | internet | c | continuing to scroll through bad news | 
cringe |  | internet | c | something embarrassing that makes you wince | 
cope |  | internet | c | a mocking term for a person's excuses or denial | 
seethe |  | internet | c | a mocking reaction describing someone as angry | 
npc |  | internet | c | a person who seems to act without independent thought, from the term non-player character in video games | 
main character energy |  | internet | c | acting as though one is the protagonist of a story | 
delulu |  | internet | c | delusional, often in a playful way, as in delulu is the solulu | 
ick |  | internet | c | a sudden feeling of disgust toward someone you were attracted to | 
situationship |  | internet | c | an undefined romantic relationship | 
red flag |  | internet | c | a warning sign in a person or relationship | 
green flag |  | internet | c | a positive sign in a person or relationship | 
gaslight gatekeep girlboss |  | internet | c | a joking triple phrase turning serious terms into a cheerful slogan | 
side quest |  | internet | c | a small task or detour outside the main goal, borrowed from role-playing games | 
lore |  | internet | c | the background story, often of a person or a joke | 
era |  | internet | c | a phase in one's life, as in my villain era | 
core |  | internet | c | a suffix that names an aesthetic, as in cottagecore | 
vibe check |  | internet | c | a test of whether the mood or energy is right | 
brainrot |  | internet | c | low-quality, absurd, or overly repetitive online content, or the mental state it supposedly causes | 
skibidi |  | internet | c | a nonsense word from the animated web series Skibidi Toilet, used as a meme | 
sigma |  | internet | c | a self-sufficient person, from the idea of the sigma male | 
ohio |  | internet | c | a meme for strange or unfortunate events, as in only in Ohio | 
mewing |  | internet | c | a practice of positioning the tongue to improve jawline appearance | 
looksmaxxing |  | internet | c | trying to maximize one's physical appearance | 
aura |  | internet | c | a measure of cool or presence, as in plus ten aura | 
aura farming |  | internet | c | acting in a way meant to gain a cool image | 
six seven |  | internet | c | a numerical meme chanted or gestured without a clear meaning | 
crash out |  | internet | c | to lose emotional control or make a reckless decision | 
locked in |  | internet | c | fully focused and determined | 
clanker |  | internet | s | a derogatory term for robots or AI, popularized online in 2025 | 
mogging |  | internet | c | outshining another person in appearance or presence | 
based |  | internet | c | holding to your own views regardless of criticism | 
stan |  | internet | c | an extremely devoted fan | 
ratio |  | internet | c | a reply that receives more likes than the original post, signaling disagreement | 
rent free |  | internet | c | occupying someone's thoughts constantly, as in living in my head rent free | 
yapping |  | internet | c | talking at length or excessively | 
rage bait |  | internet | c | content created to make people angry so they engage | 
unalive |  | internet | c | a replacement for words about death or suicide, used to avoid moderation | 
seggs |  | internet | v | a playful replacement for the word sex, used to avoid filters | 
le dollar bean |  | internet | c | a substitute for the word lesbian, used to avoid filters | 
corn |  | internet | c | a substitute for a term for adult content | 
órale | orale | mexican | c | an interjection that can mean okay, wow, come on, or right on | 
ese |  | mexican | s | a way of addressing a man, roughly dude or man | 
vato |  | mexican | c | a guy or dude | 
carnal |  | mexican | c | a close friend or brother, literally of the flesh | 
chale |  | mexican | c | an interjection of disappointment or refusal, like damn or no way | 
no manches |  | mexican | c | no way or you're kidding | 
chido |  | mexican | c | cool or great | 
neta |  | mexican | c | the truth, as in la neta | 
güey | guey, wei, wey | mexican | c | dude, a friendly address among Mexican friends | 
simón | simon | mexican | c | yes or sure | 
ahorita |  | mexican | c | right now, in a little while, or sometimes much later | 
fresa |  | mexican | c | a young person from a wealthy, preppy background | 
naco |  | mexican | s | a derogatory label for someone considered uncultured or lower class | 
chamba |  | mexican | c | a job or work | 
chamaco |  | mexican | c | a child or boy | 
morro |  | mexican | c | a kid or young person, especially in northern Mexico | 
chavo |  | mexican | c | a boy or guy | 
pinche |  | mexican | v | a vulgar intensifier meaning damn, as in pinche calor | 
chisme |  | mexican | c | gossip | 
ni modo |  | mexican | c | oh well, nothing to be done | 
aguas |  | mexican | c | watch out | 
ándale | andale | mexican | c | go ahead, hurry up, or exactly | 
híjole | hijole | mexican | c | an exclamation of surprise or dismay | 
qué onda | que onda | mexican | c | what's up, literally what wave | 
buena onda |  | mexican | c | good vibes or a friendly person | 
padre |  | mexican | c | cool or great | 
gacho |  | mexican | c | bad, ugly, or unpleasant | 
chafa |  | mexican | c | low quality | 
lana |  | mexican | c | money, literally wool | 
feria |  | mexican | c | small change or money, from a word for fair | 
chela |  | mexican | c | beer | 
chilango |  | mexican | s | a person from Mexico City | 
pocho |  | mexican | s | a Mexican American seen as having lost Spanish or Mexican culture | 
chicano |  | mexican | s | a self-chosen identity term for Mexican Americans, politicized during the civil rights movement of the 1960s | 
latinx | latine | mexican | s | gender-neutral terms for Latino people | 
jefa | jefe | mexican | c | mom and dad, literally boss | 
mija | mijo | mexican | c | my daughter and my son, used as terms of affection | 
trucha |  | mexican | c | watch out or be alert | 
ruca |  | mexican | c | a girlfriend or woman | 
ranfla |  | mexican | c | a car, especially a lowrider | 
firme |  | mexican | c | cool or good, literally firm | 
cholo | chola | mexican | s | a Chicano subculture style marked by dress and demeanor, with roots in Los Angeles | 
pachuco |  | mexican | s | a member of a Mexican American youth subculture of the 1930s and 1940s known for zoot suits and Caló | 
caló | calo | mexican | c | an argot spoken by Mexican Americans, mixing Spanish and English with Romani-influenced and Spanish slang | 
sale |  | mexican | c | okay, or deal | 
homeboy |  | mexican | c | a close friend from the same neighborhood | 
lonche |  | latino | c | lunch | 
troca |  | latino | c | truck | 
parquear |  | latino | c | to park | 
yarda |  | latino | c | a yard | 
aseguranza |  | latino | c | insurance | 
textear |  | latino | c | to text | 
rentar |  | latino | c | to rent | 
janguear |  | latino | c | to hang out | 
marqueta |  | latino | c | a market | 
boricua |  | caribe | s | a Puerto Rican, from the Taíno name Borikén | 
nuyorican |  | caribe | s | a Puerto Rican who was born or raised in New York | 
wepa |  | caribe | c | an exclamation of excitement or approval | 
pa'lante | palante | caribe | c | forward, from para adelante | 
bochinche |  | caribe | c | gossip or commotion | 
bregar |  | caribe | c | to deal with or handle something | 
chévere | chevere | caribe | c | great or cool | 
pana |  | caribe | c | friend, buddy | 
vaina |  | caribe | c | thing or matter, used for almost anything | 
dime a ver |  | caribe | c | a Dominican greeting, roughly what's up | 
qué lo qué | que lo que | caribe | c | what's up | 
tigueraje |  | caribe | c | street smarts and hustle, from the word tiguere | 
guagua |  | caribe | c | a bus | 
yuma |  | caribe | s | a Cuban word for the United States or an American | 
asere |  | caribe | c | a Cuban term for friend | 
mano |  | caribe | c | a friendly address used in the Dominican Republic and Puerto Rico, short for hermano | 
jevo | jeva | caribe | c | a boyfriend and a girlfriend in Dominican and Cuban slang | 
cipote |  | latam | c | a child, in Salvadoran Spanish | 
chivo |  | latam | c | cool in Salvadoran and Guatemalan Spanish | 
vos |  | latam | c | the informal you pronoun used in much of Central America and parts of South America | 
pisto |  | latam | c | money in Guatemalan Spanish | 
cabal |  | latam | c | exactly, in Guatemalan Spanish | 
parce | parcero | latam | c | a buddy in Colombian Spanish, especially from Medellín | 
bacano |  | latam | c | cool or great in Colombian Spanish | 
che |  | latam | c | a way of addressing someone in Argentine and Uruguayan Spanish | 
piola |  | latam | c | cool or smart in Argentine slang | 
laburo |  | latam | c | work or a job in Argentine slang | 
opo | po | filipino | c | words added to a sentence to show respect to an older person | 
kuya |  | filipino | c | older brother and older sister, also used to address older people respectfully | 
tito | tita | filipino | c | uncle and aunt, used for adult family friends and relatives | 
pasalubong |  | filipino | c | a gift brought back from a trip for family and friends | 
kilig |  | filipino | c | the fluttery feeling of romantic excitement or a cute moment | 
gigil |  | filipino | c | an overwhelming urge to squeeze or pinch something adorable | 
hugot |  | filipino | c | an emotional line drawn from personal pain or heartbreak, from the verb meaning to pull out | 
sana all |  | filipino | c | I wish everyone had that | 
charot |  | filipino | c | just kidding | 
chika |  | filipino | c | gossip or chatter | 
bes |  | filipino | c | short for beshie, meaning best friend | 
jowa |  | filipino | c | a boyfriend or girlfriend | 
gora |  | filipino | c | let's go | 
lodi |  | filipino | c | a Filipino term of respect meaning idol, formed by reversing the letters | 
petmalu |  | filipino | c | awesome, formed from the reversal of malupit | 
tara |  | filipino | c | let's go | 
sige |  | filipino | c | okay or go ahead | 
nako |  | filipino | c | an exclamation of exasperation or worry | 
susmaryosep |  | filipino | c | an exclamation of shock or exasperation, from Jesus, Mary, and Joseph | 
bahala na |  | filipino | c | come what may, or leaving it to fate | 
utang na loob |  | filipino | c | a debt of gratitude that is felt as a moral obligation | 
taglish |  | filipino | c | the mixing of Tagalog and English in one sentence | 
ewan |  | filipino | c | I don't know | 
dạ |  | seasia | c | a polite yes used to respond to an elder or someone of higher status | 
anh chị em | anh chi em | seasia | c | kinship pronouns used to address older brother, older sister, and younger person | 
ăn cơm chưa | an com chua | seasia | c | have you eaten rice yet, a greeting that shows care | 
việt kiều | viet kieu | seasia | c | an overseas Vietnamese person | 
trời ơi | troi oi | seasia | c | oh my god, literally oh sky | 
sanuk |  | seasia | c | fun or enjoyment, a Thai value | 
mai pen rai |  | seasia | c | never mind or no problem | 
kreng jai |  | seasia | c | the feeling of not wanting to impose on others | 
jai yen |  | seasia | c | a cool heart, meaning staying calm | 
nyob zoo |  | seasia | c | hello in the Hmong language | 
ua tsaug |  | seasia | c | thank you in Hmong | 
aegyo |  | korean | c | cute behavior or expressions meant to charm | 
daebak |  | korean | c | amazing or fantastic | 
hwaiting |  | korean | c | a cheer meaning fighting, used for encouragement | 
oppa | hyung, noona, unnie | korean | c | terms for older brother or older friend, depending on the speaker's gender | 
sunbae | hoobae | korean | c | senior and junior in a school or workplace | 
jjang |  | korean | c | the best or awesome | 
heol |  | korean | c | an exclamation of shock | 
kkondae |  | korean | c | a condescending older person who lectures | 
ajumma | ajusshi | korean | c | a middle-aged woman and a middle-aged man | 
mukbang |  | korean | c | a livestream or video in which a host eats a large meal while talking to viewers | 
nunchi |  | korean | c | the ability to read a room and sense others' moods | 
pali pali |  | korean | c | hurry up, repeated for emphasis | 
aigoo |  | korean | c | an exclamation of surprise or sympathy | 
hallyu |  | korean | c | the Korean Wave of pop culture exports | 
kawaii |  | anime | c | cute | 
sugoi |  | anime | c | amazing or incredible | 
yabai |  | anime | c | dangerous, but also used for something amazing or terrible | 
oshi |  | anime | c | a favorite idol or character you support | 
otaku |  | anime | c | a person with obsessive interests, especially in anime and manga | 
senpai | kohai | anime | c | a senior and a junior in school or work | 
ganbatte |  | anime | c | do your best | 
itadakimasu |  | anime | c | a phrase said before eating to express gratitude | 
kakkoii |  | anime | c | cool or stylish | 
moe |  | anime | c | a feeling of affection for a cute character | 
waifu | husbando | anime | c | a fictional character someone is devoted to, from the English words wife and husband | 
weeb |  | anime | c | a non-Japanese person who is obsessed with Japanese culture | 
isekai |  | anime | c | a story in which a person is transported to another world | 
tsundere |  | anime | c | a character who is cold at first and warm later | 
ikigai |  | anime | c | a reason for being | 
yyds |  | chinese | c | an abbreviation of yongyuan de shen, meaning forever god, a phrase of praise | 
involution |  | chinese | c | neijuan, a word for intense competition that produces little benefit | 
lying flat |  | chinese | c | tang ping, a refusal to take part in high-pressure work and consumer life | 
let it rot |  | chinese | c | bai lan, a stronger rejection of competition than lying flat | 
996 |  | chinese | c | a work schedule from 9 a.m. to 9 p.m., six days a week | 
laowai |  | chinese | s | a foreigner | 
aiya |  | chinese | c | an exclamation of surprise or frustration | 
ayi |  | chinese | c | a term for an older woman, similar to auntie | 
abc |  | chinese | s | american-born Chinese | 
fob |  | chinese | s | fresh off the boat, a label for recent immigrants | 
hongbao |  | chinese | c | a red envelope with money given at celebrations | 
guanxi |  | chinese | c | social connections and mutual obligation | 
mianzi |  | chinese | c | face, meaning social reputation | 
ganbei |  | chinese | c | cheers, literally dry the cup | 
chi fan le ma |  | chinese | c | have you eaten yet, a greeting that shows care | 
m goi |  | chinese | c | thank you or excuse me in Cantonese | 
lai see |  | chinese | c | a red packet in Cantonese tradition | 
yum cha |  | chinese | c | to drink tea, referring to a Cantonese tea and dim sum meal | 
yaar |  | desi | c | friend or buddy | 
arre |  | desi | c | an interjection used to get attention or show surprise | 
desi |  | desi | s | a person of South Asian heritage, from the Hindi word for country | 
aunty | auntie | desi | c | respectful terms for older adults, even if they are not relatives | 
jugaad |  | desi | c | a creative, improvised workaround | 
timepass |  | desi | c | an activity done just to pass time | 
prepone |  | desi | c | to move an event to an earlier time | 
bhai |  | desi | c | brother | 
didi |  | desi | c | older sister | 
bindaas |  | desi | c | carefree and cool | 
paisa vasool |  | desi | c | worth the money | 
mast |  | desi | c | great or awesome | 
kya baat hai |  | desi | c | what a thing, expressing admiration | 
bakwaas |  | desi | c | nonsense | 
hinglish |  | desi | c | the blending of Hindi and English | 
abcd |  | desi | s | american-born confused desi | 
da kine |  | hawaii | c | the thing or whatever, a placeholder word | 
brah | bruddah | hawaii | c | brother or friend | 
shoots |  | hawaii | c | okay or sounds good | 
pau |  | hawaii | c | finished | 
ono |  | hawaii | c | delicious | 
grindz |  | hawaii | c | food | 
choke |  | hawaii | c | a lot of | 
talk story |  | hawaii | c | to chat at length | 
akamai |  | hawaii | c | smart or clever | 
lolo |  | hawaii | c | crazy or silly | 
kapu |  | hawaii | c | forbidden | 
pau hana |  | hawaii | c | after work | 
howzit |  | hawaii | c | a greeting meaning how is it | 
shaka |  | hawaii | c | a hand gesture with the thumb and pinky out, meaning hang loose | 
ohana |  | hawaii | c | family | 
pupu |  | hawaii | c | an appetizer | 
hana hou |  | hawaii | c | one more time, an encore | 
slippahs |  | hawaii | c | flip-flops | 
kolohe |  | hawaii | c | mischievous | 
mo' bettah | mo bettah | hawaii | c | better | 
no can |  | hawaii | c | cannot | 
bumbye |  | hawaii | c | later or eventually | 
pc bang |  | gaming | c | a Korean internet cafe for gaming | 
gosu |  | gaming | c | an expert player | 
wibu |  | gaming | c | a Vietnamese and Indonesian word for a weeb, a fan of Japanese media | 
wah gwaan |  | jam | c | what's going on, a greeting | 
irie |  | jam | c | good, pleasant, or all right | 
yaad |  | jam | c | home, from the English word yard | 
likkle |  | jam | c | little | 
nuff |  | jam | c | a lot | 
pickney |  | jam | c | a child | 
bredda |  | jam | c | brother or friend | 
dutty |  | jam | c | dirty, also used for something rough or wicked | 
mash up |  | jam | c | to break or destroy, and also to do something excellently | 
bashment |  | jam | c | a lively party or dancehall event | 
big up |  | jam | c | to praise or give respect | 
bless up |  | jam | c | a greeting or sign-off wishing blessings | 
nyam |  | jam | c | to eat | 
duppy |  | jam | c | a ghost or spirit | 
tun up |  | jam | c | to turn up, meaning to raise the energy at a party | 
link up |  | jam | c | to meet up | 
soon come |  | jam | c | I will be there eventually, not necessarily soon | 
cyaan |  | jam | c | can't | 
unu |  | jam | c | you, plural | 
rude boy |  | jam | c | a young person with a street attitude, from ska and rocksteady culture | 
lime |  | westindies | c | to hang out casually, or a casual social gathering | 
fete |  | westindies | c | a party, often with music | 
wine |  | westindies | c | to dance with a rolling motion of the hips | 
doh |  | westindies | c | don't | 
ent |  | westindies | c | isn't it, a tag question | 
bacchanal |  | westindies | c | chaos, scandal, or a wild celebration | 
mamaguy |  | westindies | c | to tease or deceive someone playfully | 
steups |  | westindies | c | the sound of sucking the teeth to express annoyance | 
tabanca |  | westindies | c | heartbreak or longing after a breakup | 
jumbie |  | westindies | c | a spirit or ghost | 
wuh loss |  | westindies | c | an exclamation of surprise or dismay | 
whappen |  | westindies | c | what's happening, a greeting | 
sak pase |  | westindies | c | what's up, in Haitian Creole | 
nap boule |  | westindies | c | we're hanging in there, a response to sak pase | 
kompa |  | westindies | c | a Haitian dance music genre | 
abeg |  | africa | c | please | 
wahala |  | africa | c | trouble or problem | 
gist |  | africa | c | gossip or a story, as in what's the gist | 
japa |  | africa | c | to flee or emigrate, especially to find better opportunities | 
sapa |  | africa | c | being broke | 
oga |  | africa | c | boss or sir | 
owambe |  | africa | c | a lavish party | 
chop |  | africa | c | to eat | 
vex |  | africa | c | to be angry | 
sabi |  | africa | c | to know | 
wetin |  | africa | c | what | 
oya |  | africa | c | come on or let's go | 
pikin |  | africa | c | a child | 
gbedu |  | africa | c | heavy, danceable beats | 
charley |  | africa | c | a friendly term for a friend in Ghana, also spelled chale | 
yawa |  | africa | c | trouble | 
sasa |  | africa | c | now or hi, in Kenyan Sheng | 
poa |  | africa | c | cool or fine | 
niaje |  | africa | c | how are you in Sheng | 
manze |  | africa | c | an exclamation that means man or wow | 
lekker |  | africa | c | nice or good, from Afrikaans | 
eish |  | africa | c | an expression of surprise or frustration | 
braai |  | africa | c | a barbecue | 
now now |  | africa | c | in a little while | 
amapiano |  | africa | c | a South African house music genre that became global | 
ubuntu |  | africa | c | the idea that people are connected, often summed up as I am because we are | 
wagwan |  | uk | c | what's going on, in MLE spelling | 
peng |  | uk | c | attractive or excellent | 
bare |  | uk | c | a lot of or very, as in bare people | 
allow it |  | uk | c | forget it or stop | 
wasteman |  | uk | s | a useless or lazy person | 
mandem |  | uk | c | a group of men or friends | 
roadman |  | uk | s | a young man associated with street culture | 
ends |  | uk | c | one's neighborhood | 
peak |  | uk | c | unfortunate or disappointing | 
long |  | uk | c | tedious or requiring too much effort | 
bait |  | uk | c | obvious | 
buzzin |  | uk | c | very happy or excited | 
mugged off |  | uk | c | made a fool of | 
skeen |  | uk | c | I see or I understand | 
ting |  | uk | c | a thing, or an attractive person | 
blud |  | uk | c | friend | 
bruv |  | uk | c | brother or friend | 
oh my days |  | uk | c | an exclamation of surprise | 
safe |  | uk | c | cool, or thanks | 
innit |  | uk | c | isn't it | 
chuffed |  | brit | c | pleased or proud about something that has happened | 
knackered |  | brit | c | exhausted | 
skint |  | brit | c | broke or without money | 
gutted |  | brit | c | very disappointed or devastated | 
mint |  | brit | c | excellent | 
banter |  | brit | c | playful teasing between friends | 
cuppa |  | brit | c | a cup of tea | 
naff |  | brit | c | unfashionable or tasteless | 
polari |  | brit | c | a form of slang used by gay men, theatre performers, and others in Britain during the twentieth century | 
fit |  | brit | c | attractive | 
proper |  | brit | c | very or truly, as in proper cold | 
blimey |  | brit | c | an exclamation of surprise | 
bloke |  | brit | c | a man | 
kip |  | brit | c | a nap or sleep | 
cheeky |  | brit | c | playfully impertinent | 
mate |  | brit | c | friend or buddy | 
craic |  | irish | c | fun, news, or enjoyable company | 
grand |  | irish | c | fine or okay | 
eejit |  | irish | c | a fool | 
banjaxed |  | irish | c | broken or ruined | 
deadly |  | irish | c | excellent | 
giving out |  | irish | c | complaining | 
yoke |  | irish | c | a thing, used when the speaker cannot remember or does not want to name it | 
culchie |  | irish | s | a person from the rural parts of Ireland | 
sláinte | slainte | irish | c | cheers, literally health | 
wee |  | scotwales | c | small | 
braw |  | scotwales | c | excellent or fine | 
bairn |  | scotwales | c | child | 
dinnae |  | scotwales | c | do not | 
ken |  | scotwales | c | to know | 
dreich |  | scotwales | c | dreary, gray, and wet, used for weather | 
blether |  | scotwales | c | to chat at length or to talk nonsense | 
numpty |  | scotwales | c | a fool | 
cwtch |  | scotwales | c | a cuddle or a cozy space | 
lush |  | scotwales | c | lovely or delicious | 
hiraeth |  | scotwales | c | a deep longing for a home or a past that may no longer exist | 
butty |  | scotwales | c | a friend or mate, used in South Wales | 
arvo |  | aus | c | afternoon | 
servo |  | aus | c | a service station | 
heaps |  | aus | c | a lot | 
sook |  | aus | c | a person who is timid or complains too easily | 
cozzie |  | aus | c | a swimsuit | 
thongs |  | aus | c | flip-flops in Australian English | 
ute |  | aus | c | a pickup truck | 
bogan |  | aus | s | a person seen as unsophisticated | 
maccas |  | aus | c | McDonald's | 
fair dinkum |  | aus | c | genuine or true | 
yeah nah |  | aus | c | a polite no that begins with yes | 
selfie |  | aus | c | a photograph a person takes of themselves | 
chur |  | aus | c | thanks or cool | 
sweet as |  | aus | c | great or excellent | 
jandals |  | aus | c | flip-flops | 
dairy |  | aus | c | a small corner shop | 
yalla |  | arab | c | let's go or hurry up | 
habibi | habibti | arab | c | my beloved, used as an affectionate address for a man and a woman | 
wallah | wallahi | arab | c | I swear by God, an oath used to emphasize honesty | 
inshallah |  | arab | c | god willing, used when talking about the future | 
mashallah |  | arab | c | as God has willed, used to express admiration or to ward off envy | 
khalas |  | arab | c | enough, finished, or that's it | 
yaani |  | arab | c | it means, a discourse marker similar to like or I mean | 
sahtein |  | arab | c | to your health, said to someone who is eating or has just eaten | 
tayeb |  | arab | c | okay or good | 
akhi | ukhti | arab | c | my brother and my sister, used among Muslim friends | 
bismillah |  | arab | c | in the name of God, said before beginning an action | 
haram |  | arab | c | forbidden and permitted, used jokingly to describe unfairness or approval | 
arabizi |  | arab | c | a way of writing Arabic in Latin letters with numbers for sounds that have no Latin equivalent | 
joon |  | arab | c | dear, used after a name as an affectionate marker | 
azizam |  | arab | c | my dear | 
taarof |  | arab | c | a system of ritual politeness in Persian culture, including offering and refusing several times | 
jigar |  | arab | c | liver, used as a term of deep affection for a loved one | 
uso |  | pasifika | c | sibling or close friend in Samoan | 
palagi |  | pasifika | s | a person who is not Samoan, usually of European descent | 
fa'a samoa | faa samoa | pasifika | c | the Samoan way, referring to the cultural system of family, village, and chiefly leadership | 
fia |  | pasifika | c | a prefix meaning wanting to be, as in fia poto, acting smart | 
malo |  | pasifika | c | hello, thanks, or well done in Samoan and Tongan | 
alofa |  | pasifika | c | love in Samoan | 
ofa |  | pasifika | c | love in Tongan | 
kia ora |  | pasifika | c | a Maori greeting meaning be well or thank you | 
whanau |  | pasifika | c | extended family in Maori | 
mana |  | pasifika | c | personal or collective authority, prestige, and spiritual power | 
aroha |  | pasifika | c | love, compassion, or empathy in Maori | 
mahi |  | pasifika | c | work | 
hui |  | pasifika | c | a meeting or gathering in Maori | 
skoden |  | native | c | let's go then, a phrase from Indigenous youth slang | 
ndn |  | native | s | an abbreviation of Indian used by Native people, often with pride | 
rez |  | native | c | reservation | 
indian time |  | native | s | a flexible approach to schedules in which events start when the people are ready | 
frybread |  | native | c | a deep-fried bread associated with many Native communities | 
powwow |  | native | c | a gathering of Native people with dancing, singing, and honoring traditions | 
yá'át'ééh | ya'at'eeh, yaateeh, yáátééh | native | c | hello in Navajo | 
ahéhee' | ahehee, ahehee', ahéhee | native | c | thank you in Navajo | 
boozhoo |  | native | c | hello in Ojibwe | 
miigwech |  | native | c | thank you in Ojibwe | 
tansi |  | native | c | hello in Cree | 
schlep |  | yiddish | c | to carry or travel with effort | 
chutzpah |  | yiddish | c | audacity or nerve | 
mensch |  | yiddish | c | a decent and honorable person | 
kvetch |  | yiddish | c | to complain | 
nosh |  | yiddish | c | to snack, or a snack | 
oy vey |  | yiddish | c | an exclamation of dismay | 
schmooze |  | yiddish | c | to chat in a friendly or networking way | 
mazel tov |  | yiddish | c | congratulations, literally good luck | 
kvell |  | yiddish | c | to feel proud, especially of a child or friend | 
klutz |  | yiddish | c | a clumsy person | 
tchotchke |  | yiddish | c | a small decorative object | 
glitch |  | yiddish | c | a minor malfunction | 
spiel |  | yiddish | c | a long persuasive speech | 
bupkis |  | yiddish | c | nothing, or something worthless | 
mishegas |  | yiddish | c | craziness or foolish behavior | 
shtick |  | yiddish | c | a performer's routine or an attention-getting trait | 
bubbe | zayde | yiddish | c | grandmother and grandfather in Yiddish | 
paisan |  | italian | c | a fellow countryman or friend, from paesano | 
mangia |  | italian | c | eat, an Italian command used in family settings | 
capisce |  | italian | c | do you understand | 
gravy |  | italian | c | a tomato-based sauce for pasta, in some Italian American families | 
gabagool |  | italian | c | cured pork, a regional pronunciation of capicola | 
madonn' | madonn | italian | c | an exclamation of surprise, shortened from Madonna | 
lagniappe |  | cajun | c | a little something extra, such as a bonus given with a purchase | 
cher |  | cajun | c | dear, used as an affectionate address | 
fais do-do | fais do do | cajun | c | a Cajun dance party | 
laissez les bons temps rouler |  | cajun | c | let the good times roll | 
making groceries |  | cajun | c | going grocery shopping, a New Orleans phrase | 
neutral ground |  | cajun | c | the median strip of a road | 
second line |  | cajun | c | a parade of people who follow a brass band, especially in New Orleans Black social aid and pleasure club traditions | 
yat |  | cajun | c | a New Orleans accent, from the greeting where y'at | 
who dat |  | cajun | c | a chant used by supporters of the New Orleans Saints | 
pass a good time |  | cajun | c | to spend time enjoying oneself, from passer un bon temps | 
bayou |  | cajun | c | a slow-moving stream or marshy waterway | 
goober |  | gullah | c | a peanut | 
gumbo |  | gullah | c | a stew, or the okra it was first named for | 
cooter |  | gullah | c | a turtle | 
haint blue |  | gullah | c | a pale blue paint used on porch ceilings, said to keep spirits away | 
binya | comya | gullah | c | a native-born islander and a newcomer, from been here and come here | 
plat-eye | plat eye | gullah | c | a shape-shifting spirit in Gullah Geechee folklore | 
tabby |  | gullah | c | a building material made from oyster shell, sand, and lime | 
camper |  | gaming | c | a player who stays in one hidden spot to ambush opponents | 
noscope |  | gaming | c | a kill made with a sniper rifle without looking through the scope | 
peek |  | gaming | c | to briefly expose yourself around a corner to see or shoot an enemy | 
rush |  | gaming | c | an aggressive early attack by a whole team | 
flank |  | gaming | c | to attack from the side or behind | 
wallhack |  | gaming | c | cheating software that lets a player see enemies through walls | 
aimbot |  | gaming | c | cheating software that automatically aims at opponents | 
smurf |  | gaming | c | an experienced player who uses a new account to face weaker opponents | 
boosting |  | gaming | c | having a stronger player raise your rank or account level | 
nerf | buff | gaming | c | to weaken or strengthen a character, weapon, or ability in a patch | 
meta |  | gaming | c | the currently dominant strategy or the set of strongest choices in a game | 
op |  | gaming | c | overpowered, meaning too strong for the balance of the game | 
elo hell |  | gaming | c | the belief that a player is stuck in a low rank because of bad teammates | 
hardstuck |  | gaming | c | unable to rise above a certain rank | 
diff |  | gaming | c | to be much better than an opponent, as in mid diff | 
afk |  | gaming | c | away from keyboard | 
noob |  | gaming | c | a beginner, often used as an insult | 
respawn |  | gaming | c | to return to life after dying in a game | 
spawn camping |  | gaming | c | waiting near the spot where opponents reappear and killing them repeatedly | 
gank |  | gaming | c | to ambush an enemy with extra players | 
jungle |  | gaming | c | the area between lanes where neutral monsters live, and the role of a player who moves through it | 
inting |  | gaming | c | deliberately dying over and over to feed the enemy team | 
feeding |  | gaming | c | dying repeatedly and giving the other team gold and experience | 
mid or feed |  | gaming | c | a demand that a player choose the middle lane or deliberately lose | 
macro |  | gaming | c | long-term strategy such as objectives and map movement, in contrast to micro | 
micro |  | gaming | c | precise control of individual units or characters | 
tank |  | gaming | c | a character built to absorb damage and protect others | 
dps |  | gaming | c | damage per second, or a player whose job is to deal damage | 
healer |  | gaming | c | a character who restores health to allies | 
aggro |  | gaming | c | the attention of an enemy, from the word aggression | 
raid |  | gaming | c | a large cooperative challenge for many players | 
wipe |  | gaming | c | when an entire group dies in a fight | 
pug |  | gaming | c | a pick-up group assembled from strangers | 
grind |  | gaming | c | repetitive play to gain experience, money, or items | 
loot |  | gaming | c | items collected from enemies or chests | 
rng |  | gaming | c | random number generator, used for luck in a game | 
ult |  | gaming | c | an ultimate ability, the strongest skill of a character | 
cooldown |  | gaming | c | the time before an ability can be used again | 
kiting |  | gaming | c | attacking while moving to avoid being hit | 
git gud |  | gaming | c | an imperative to get good, often used mockingly | 
you died |  | gaming | c | the message shown when the player dies in Dark Souls games | 
bonfire |  | gaming | c | a checkpoint in Dark Souls where players rest and restore health | 
neutral |  | gaming | c | the part of a fight when neither player has an advantage | 
footsies |  | gaming | c | a spacing battle in which players try to hit each other at the edge of their range | 
whiff punish |  | gaming | c | hitting an opponent right after their attack misses | 
okizeme |  | gaming | c | the situation in which one player attacks an opponent who is getting up | 
mix-up | mix up | gaming | c | an attack that forces the opponent to guess between options | 
zoning |  | gaming | c | controlling distance with projectiles and long-range attacks | 
frame data |  | gaming | c | the numbers that describe the speed and recovery of every move | 
rollback netcode |  | gaming | c | a networking method that keeps online fighting games responsive | 
button masher |  | gaming | c | a player who presses buttons randomly rather than using planned moves | 
any percent |  | gaming | c | a speedrun category in which the goal is to finish the game as fast as possible by any means | 
glitchless |  | gaming | c | a speedrun category that prohibits glitches | 
rta |  | gaming | c | real-time attack, a timing method that counts actual elapsed time | 
tas |  | gaming | c | tool-assisted speedrun, a run made with software that allows frame-by-frame input | 
pb |  | gaming | c | personal best | 
sequence break |  | gaming | c | to perform actions in an order the designers did not intend | 
frame perfect |  | gaming | c | an action that must be done on one exact frame | 
games done quick |  | gaming | c | a series of speedrunning marathons that raise money for charity | 
obby |  | gaming | c | an obstacle course in Roblox | 
robux |  | gaming | c | the virtual currency used in Roblox | 
tycoon |  | gaming | c | a game genre in which players build and manage a business | 
creeper |  | gaming | c | a green explosive monster in Minecraft | 
redstone |  | gaming | c | a Minecraft material used to build circuits | 
griefing |  | gaming | c | deliberately ruining other players' work or experience | 
victory royale |  | gaming | c | the win screen in Fortnite | 
zero build |  | gaming | c | a Fortnite mode without building mechanics | 
whale |  | gaming | c | a player who spends a large amount of money in a free-to-play game | 
gacha |  | gaming | c | a game mechanic in which players pull random items using a currency | 
pay to win |  | gaming | c | a game in which paying money provides a major advantage | 
loot box |  | gaming | c | a purchased container with random rewards | 
simlish |  | gaming | c | the nonsense language spoken in The Sims games | 
plumbob |  | gaming | c | the green diamond above a Sim's head | 
bells |  | gaming | c | the currency in Animal Crossing | 
turnip stalk market |  | gaming | c | the in-game trading of turnips in Animal Crossing | 
""".strip()

EVERYDAY = frozenset({'996', 'abc', 'akamai', 'alofa', 'anh chị em', 'aunty', 'badges', 'bail', 'banter', 'bayou', 'bells', 'bloke', 'bogus', 'bonfire', 'boosting',
 'buggy', 'butty', 'cabal', 'carnal', 'carry', 'category', 'che', 'cheese', 'cher', 'chivo', 'choke', 'chop', 'coke', 'cool', 'cooldown', 'cooter',
 'corn', 'creeper', 'dairy', 'dap', 'deadly', 'def', 'didi', 'directly', 'doh', 'duckwalk', 'emo', 'ent', 'ewan', 'feeding', 'feria', 'fete', 'fia',
 'flank', 'fly', 'frame data', 'frappe', 'gist', 'giving out', 'glitch', 'glitchless', 'goober', 'goth', 'grand', 'gravy', 'green', 'gumbo', 'haram',
 'hater', 'healer', 'hip', 'hoagie', 'holler', 'hon', 'house', 'hui', 'involution', 'jimmies', 'jungle', 'kapu', 'ken', 'kip', 'kiting', 'klutz',
 'lana', 'legendary', 'let it rot', 'lime', 'lobby', 'lodi', 'lolo', 'loot box', 'lush', 'lying flat', "ma'am", 'macro', 'mad', 'mahi', 'malo',
 'mana', 'mano', 'mash', 'mast', 'micro', 'mint', 'mix-up', 'moe', 'nako', 'neutral', 'neutral ground', 'nosh', 'now now', 'ofa', 'ohana', 'ollie',
 'on line', 'ono', 'opo', 'oya', 'padre', 'pana', 'pau', 'pay to win', 'pb', 'peek', 'ping', 'plumb', 'poa', 'pocket', 'poke', 'powwow', 'pro-am',
 'proper', 'pug', 'pupu', 'raid', 'receipts', 'redstone', 'regular coffee', 'rez', 'rotary', 'rta', 'rush', 'sabi', 'sale', 'sasa', 'schlep', 'scrub',
 'second line', 'selfie', 'shoots', 'simón', 'spiel', 'squad', 'steady', 'stoop', 'sugar', 'supper', 'supper club', 'swag', 'tabby', 'tailgate',
 'tank', 'tara', 'tas', 'the cities', 'the park', 'the t', 'thongs', 'tote', 'tycoon', 'ubuntu', 'up north', 'uso', 'ute', 'vex', 'vogue', 'vos',
 'walking', 'wee', 'whale', 'wine', 'wipe', 'yat', 'yoke', 'you died', 'zoning'})

DETAILS = {'finna': ('It is derived from fixing to, a Southern American form, and long used in Black Southern speech before its online spread.',
           'It is now common across the internet, though outside users sometimes treat it only as a joke word.',
           "I'm finna head to the store if anybody needs anything."),
 "ain't": ('It is an old English form found in many nonstandard dialects, not unique to AAE.',
           'It is stigmatized in formal settings but common across many communities, so using it is not itself a marker of one group.',
           "Ain't nobody told me the schedule changed this morning."),
 'steady': ('It is documented in Black English and often heard in Southern speech.',
            'It can express admiration or exasperation depending on the tone.',
            'He steady talking while the whole room is trying to listen.'),
 'bout to': ('It is common in AAE and in many other casual American speech styles.',
             'The written bouta variant is widespread in text messages.',
             "I'm bouta pull up if the traffic lets up."),
 'ion': ('It is a texting-era spelling that spread through social media and became strongly tied to Black online speech.',
         'It is mainly written, since spoken versions blend into ordinary fast speech.',
         'Ion think the store opens until noon on Sunday.'),
 'bet': ('It is rooted in African American English and long used in hip-hop spaces before spreading through TikTok and gaming chat.',
         'Because it is so short and flexible, outsiders often use it without realizing it signals a specific kind of casual agreement.',
         "You can bring the chairs, and I'll handle the speakers, bet."),
 'cap': ('It is commonly traced to Southern Black speech and hip-hop, and boosted by Atlanta artists in the 2010s.',
         'No cap, meaning no lie, turned into a general intensifier across online youth culture.',
         'That story sounds like cap, because nobody saw it happen.'),
 'no cap': ('The phrase is the negated form of cap, and it circulated heavily in rap lyrics and on social media in the late 2010s.',
            'It is now widely used as a sentence-ending mark of honesty among many groups.',
            'The new pizza spot is the best in town, no cap.'),
 'lit': ('In earlier Black speech it could mean intoxicated, and by the 2010s it broadened to mean a great party or event.',
         'It is widely used and generally neutral, though it now feels older to some young speakers.',
         'The block party was lit from the first song to the last.'),
 'slaps': ('It grew out of Black online and hip-hop usage in the 2010s.',
           'It works as a verb of praise, so it is usually applied to songs.',
           'That new playlist opener slaps every single time.'),
 'fire': ('It is used in hip-hop for decades, and also for praise for lyrics and outfits.',
          'It can sound dated in some circles but remains common.',
          'His verse on that track was fire from the first bar.'),
 'drip': ('It is commonly attributed to Southern hip-hop and Atlanta rap in the mid-2010s.',
          'It can describe a single piece of clothing or a whole presentation.',
          'He walked in with so much drip that the cameras turned around.'),
 'bae': ('It is commonly said to derive from babe or baby, and spread through Black Twitter in the early 2010s before reaching mainstream.',
         'Some Black users note it was in their communities long before it was marketed.',
         "I'm taking bae to dinner after the concert."),
 'salty': ('It is a longstanding term in African American English that became widespread on social media.',
           'It often implies the speaker is holding a grudge.',
           "He's still salty that nobody picked his song."),
 'extra': ('It is a Black American slang usage that spread widely online in the 2010s.',
           'It can be playful or mildly critical depending on tone.',
           'She brought a full banner and confetti for a casual lunch, which is so extra.'),
 'thirsty': ('It spread through Black Twitter in the 2010s from older uses of the word.',
             'It carries a mild put-down, especially in dating talk.',
             'He commented on every single post, which was a little thirsty.'),
 'clapback': ('It was popularized by Black Twitter users who turned the reply into a recognized genre.',
              'The term is often used to praise a response, not just describe it.',
              'Her clapback to the rumor had everyone reposting it within the hour.'),
 'woke': ('The phrase stay woke appears in Black American music and speech from the early twentieth century, and the word later became a general '
          'political label.',
          'Its meaning has shifted in mainstream debate, so using it now can be politically loaded.',
          'He told us to stay woke about how the new policy would affect the neighborhood.'),
 'cuffing season': ('The phrase was popularized in hip-hop and Black social media circles in the 2010s, with cuffing referring to handcuffs as a '
                    'metaphor for commitment.',
                    'People joke about it each autumn, when group chats fill with predictions about who will be paired off by winter.',
                    'Once the weather turns, the group chat starts talking about cuffing season.'),
 'on god': ('It is common in hip-hop and Black youth speech, and later popular across online communities.',
            'It is an affirmation rather than a religious statement.',
            "I'm not lying, on god, the bus was already gone."),
 'bussin': ('It was popularized by Black American teens and then by TikTok, with some earlier use as a descriptor of excellence.',
            'Because it spread so quickly, many users now use it ironically.',
            "That peach cobbler was bussin, and I'm going back for more."),
 'gang gang': ('It is taken from gang affiliation language in hip-hop and spread as an all-purpose expression of solidarity.',
               'The original connection to gang loyalty means some users avoid it or adopt it with caution.',
               'We finished the tournament undefeated, gang gang.'),
 'opps': ('It is associated with drill and gang-related rap from Chicago and then adopted more widely.',
          'It can be used jokingly online but originates in a violent context.',
          'The comment section turned into a wall of opps after the rivalry post.'),
 'tweaking': ('The usage comes from African American English and grew from the older drug-related meaning.',
              'It is common in friendly teasing.',
              "You must be tweaking if you think I'm walking that far."),
 'pressed': ('It is common in AAE and in internet speech.',
             'It often carries a hint that the worry is unnecessary.',
             'Why are you so pressed about who sat in the front row.'),
 "boo'd up": ('The phrase is African American English wordplay on boo, an affectionate name for a partner, and it spread through social media '
              'captions in the 2010s.',
              'It usually appears in photo captions and group chats when someone is spending most of their free time with a partner.',
              "He's been boo'd up since the summer and hardly texts back."),
 'chile': ("It is popular in Black women's speech and widely associated with the Black Southern manner of speaking.",
           'Outsiders often use it for humor without realizing it signals familiarity.',
           'Chile, the line at that place was out the door.'),
 'receipts': ('It was popularized on Black Twitter in the 2010s.',
              'It is used in arguments, accusations, and friendly joking.',
              "I have the receipts from when she said she'd be there."),
 'caught in 4k': ('It is a Black Twitter phrase from the late 2010s that referred to the clarity of ultra high definition video.',
                  'The phrase works as a joking reference to recorded proof.',
                  'He said he was home sick, but he was caught in 4K at the mall.'),
 'lemme find out': ('It is a conversational pattern popular on Black Twitter and TikTok.',
                    'The tone makes it clear that the speaker is teasing.',
                    'Lemme find out you ate the last slice without telling anybody.'),
 "i'm weak": ("It belongs to a family of Black Twitter reaction phrases, including I'm dead and I'm deceased, that turn laughter into mock collapse.",
              'The expression works as exaggeration, and outsiders sometimes take it literally when they see it in a comment thread.',
              'That video of the cat sliding off the table has me weak.'),
 "it's the ___ for me": ('It is commonly circulated on Black Twitter and TikTok in the early 2020s.',
                         'The frame works as a structure more than a fixed phrase.',
                         "It's the way he paused before the punchline for me."),
 'periodt': ('It was popularized by Black women and Black social media creators in the 2010s as an elongated spelling of period.',
             'The spelling signals emphasis and finality.',
             'The decision is made, periodt.'),
 'gassed': ('It is used in hip-hop culture and in British slang with related meanings.',
            'It can refer to being excited or to flattering someone.',
            'The crowd got me gassed before I even stepped on stage.'),
 'gas': ("The usage comes from African American English and hip-hop, where gas suggests fuel that powers someone's confidence.",
         'Gas can be positive praise, as in gassing someone up, or a gentle warning that flattery has gone too far.',
         "Y'all keep gassing me up for a haircut I haven't gotten yet."),
 'secure the bag': ('It spread in hip-hop and Black social media in the 2010s.',
                    'It can describe ambition in a positive way.',
                    "He's busy this month because he's trying to secure the bag before school starts."),
 'flex': ('It is a hip-hop term with older roots in Black youth speech.',
          'It can be a playful brag or a criticism depending on tone.',
          'He flexed his new sneakers in every group photo.'),
 'pull up': ('Hip-hop lyrics and Black social media helped popularize the phrase for arriving somewhere in person, often with swagger.',
             'Depending on tone it can be a friendly invitation to join the group or a challenge to someone who has been talking big.',
             "If you're hungry, pull up and we'll cook something."),
 'swag': ('It is a hip-hop term of the 2000s derived from swagger.',
          'It became a mainstream marketing word, which made many original users stop using it.',
          'He walked into the gym with a lot of swag and a brand-new bag.'),
 'dap': ('It is commonly traced to Black soldiers in the Vietnam era as a coded greeting, though accounts vary.',
         'The gesture itself carries meaning beyond the word.',
         'The coach gave each player a dap as they left the court.'),
 'word up': ('The phrase comes from New York hip-hop in the 1980s, and the song Word Up by Cameo in 1986 spread it nationally.',
             'The shortened word works the same way.',
             "Word, I'll meet you at the corner after class."),
 'dope': ('Hip-hop usage from the 1980s grew out of an older drug-related meaning.',
          'The shift in meaning shows how slang can reverse its original sense.',
          'That mural on the side of the building is dope.'),
 'def': ('It is popular in 1980s hip-hop and connected to the label Def Jam.',
         'It is now mostly nostalgic or historical.',
         'The remix was def from the first beat.'),
 'phat': ('It is a 1990s hip-hop expression sometimes explained as an acronym, though that explanation is generally treated as a backronym.',
          'It is mostly dated now.',
          'That beat was phat, and the room knew it.'),
 'fly': ('It is a long-running term in Black American slang stretching back at least to the 1970s.',
         'It is usually used for appearance and attitude.',
         'She walked in looking fly from head to toe.'),
 'crib': ('It was popularized in hip-hop in the 1990s and widely used after the show MTV Cribs.',
          'The word has become broadly familiar.',
          "We're meeting at my crib before the game."),
 'bling': ('It was popularized by the Cash Money Records song Bling Bling in 1999.',
           'The word entered dictionaries within a few years.',
           'His chain had so much bling that people noticed it from across the room.'),
 'grillz': ('It is associated with Southern hip-hop and widely linked to Houston rapper Paul Wall in the 2000s.',
            'The word is used for both the jewelry and the aesthetic.',
            'He flashed a gold grill when he smiled at the camera.'),
 'cool': ('Scholars connect the sense of cool in American speech to Black jazz culture of the mid-twentieth century and earlier West African ideas '
          'of composure.',
          'The word is now so general that its history is often forgotten.',
          'The new drummer kept everything cool even when the tempo changed.'),
 'hip': ('It is related to hep and hepcat in jazz culture, with dispute among linguists about deeper West African roots.',
         'It shows how Black musical communities shaped general American vocabulary.',
         'He always knew the hip places before they got crowded.'),
 'mad': ('It is strongly associated with New York hip-hop and Northeast Black and Latino speech.',
         'It spread across the country but retains a New York flavor.',
         'The line at the bakery is mad long today.'),
 'deadass': ('It is associated with New York City, especially Black and Latino communities, before spreading online.',
             'It works as both an intensifier and a way to ask if the listener is serious.',
             'Deadass, I left my keys on the counter ten minutes ago.'),
 'jawn': ('It is associated with Philadelphia Black English, with documented use in the region for decades.',
          'Outside Philadelphia it is mostly a regional marker and is often used playfully.',
          'Pass me that jawn on the table, the blue one.'),
 'hyphy': ('It is associated with the Bay Area hip-hop movement of the 2000s, with artists such as Mac Dre and E-40.',
           'The word names both a sound and a way of dancing.',
           'The whole street turned hyphy the moment the car stereo came on.'),
 'going dumb': ('It comes from Bay Area hip-hop vocabulary in which dumb is a positive intensifier.',
                'The word dumb here is not an insult.',
                'The crowd went dumb as soon as the bass dropped.'),
 'hella': ('It is associated with Northern California, especially Oakland and the Bay Area, and used in many communities there.',
           'It spread nationally but is still a regional marker.',
           'There were hella people at the market this morning.'),
 'mane': ('It is associated with Houston and Texas Black speech and Southern hip-hop.',
          'The spelling in writing signals a particular regional sound.',
          'Mane, you should have seen the lines at the car show.'),
 'slab': ('It is documented in Houston hip-hop and car show culture.',
          'The acronym is a part of the culture, so the cars are as much a symbol as a word.',
          'He drove his slab down the avenue with the trunk music playing.'),
 'trill': ('It was popularized by the Port Arthur, Texas group UGK in the 1990s.',
           'It is used as an adjective of respect.',
           'His story felt trill because he never tried to impress anyone.'),
 'crunk': ('It is associated with Southern hip-hop and popularized by Lil Jon and the Eastside Boyz in the early 2000s.',
           'It names both a mood and a genre.',
           'The stadium got crunk when the home team scored the final point.'),
 'turnt': ('It comes from turned up, widespread in Southern hip-hop and online youth culture.',
           'The double meaning of excitement and intoxication depends on context.',
           'We were turnt before the first song even finished.'),
 'trap': ('It is associated with Atlanta hip-hop from the early 2000s.',
          'The genre name has far outgrown the original reference.',
          'The trap beat on that song has a rolling bass line that shakes the car.'),
 'bando': ('It comes from trap music vocabulary, popularized by Atlanta rappers.',
           'It can be used ironically to mean a messy home.',
           'The dorm room looked like a bando after finals.'),
 'screwed': ('It was created by Houston DJ Screw and his circle in the early 1990s.',
             'It is a documented example of a local sound that shaped national hip-hop.',
             'The late night playlist was all screwed and chopped, slow and heavy.'),
 'go-go': ('It is credited to Chuck Brown, widely called the Godfather of Go-Go, in the 1970s.',
           'The genre remains central to D.C. identity, and its call-and-response style shaped local speech.',
           'The block party had a go-go band that kept the crowd moving for hours.'),
 'ratchet': ('It is traced to a Louisiana pronunciation of wretched and used among Black women before spreading.',
             'It can be playful or classist depending on who says it, so it deserves caution.',
             'The group chat got a little ratchet when the argument started.'),
 'bougie': ('It comes from bourgeois, widely used in Black American speech and later spread.',
            'It can be affectionate or critical depending on tone.',
            'He ordered the fancy tea and said it was too bougie for him.'),
 'what it do': ('The greeting is associated with Black American English, particularly in the South and Midwest, and appears frequently in 1990s '
                'hip-hop.',
                'People answer it with a short report such as nothing much or just chilling, which makes it a greeting and a question at once.',
                'What it do, everybody, thanks for coming out tonight.'),
 'kick it': ('The phrase is long-running Black American slang that was popularized in 1990s hip-hop.',
             'It appears in many other communities now.',
             'We can kick it at the park until the sun goes down.'),
 'bruh': ('It is a variant of brother used in Black speech and widespread on social media.',
          'It can express disbelief when used alone.',
          'Bruh, that cannot be the final score.'),
 'boo': ('The word comes from African American English, with wide use in the 1990s and 2000s.',
         'It can carry romantic or platonic warmth.',
         "I'm picking up my boo from the airport tonight."),
 'hater': ('It was popularized in 1990s hip-hop, with the phrase playa hater common in the period.',
           'It is now a general term of mock complaint.',
           "Don't pay attention to the haters, just keep doing the work."),
 'squad': ('It grew out of hip-hop and spread through teen culture.',
           'It is a neutral word that works for friend groups and teams.',
           'My squad is already in line for the concert.'),
 'homie': ('The term is shared between Black and Chicano communities in Los Angeles and entered national slang through hip-hop and film in the 1980s '
           'and 1990s.',
           'It signals a friend who shares your neighborhood or background, and it is closer than an ordinary acquaintance.',
           "He's my homie from the old neighborhood."),
 'house': ('It was formalized in New York ballroom beginning in the 1970s, with houses such as LaBeija, Xtravaganza, and Ninja.',
           'The word has a family meaning that goes beyond a simple team name.',
           'She joined the house when she was nineteen and has treated it like family since.'),
 'mother': ('It is documented in ballroom culture and widely discussed in accounts of chosen family.',
            'Online, mother is also used as high praise for someone who performs brilliantly, which stretches the original meaning.',
            'The house mother organized a fundraiser for a member who needed a safe place to stay.'),
 'category': ('The category system is the core structure of ballroom competition and appears in documentary accounts from the 1980s onward.',
              'Categories include themes such as realness, runway, and face, each with its own rules.',
              'The category for the night was executive realness, so everyone arrived in tailored suits.'),
 'realness': ('It is described in Paris Is Burning as a ballroom category and standard of excellence.',
              'The term has complicated social meaning because it can connect to safety in the outside world.',
              'She won the category because her realness was so convincing the judges did not speak.'),
 'walking': ('The verb comes from walking the runway, which is the central performance in many categories.',
             'To walk a ball means to take part in it.',
             'He is walking three categories tonight and has been practicing for weeks.'),
 'vogue': ('It was developed in ballroom, with Harlem dancers such as Willi Ninja in the 1980s and a lineage that includes the earlier practice of '
           'performance.',
           'The dance was widely commercialized after a 1990 pop song used the name, which led to debate about credit.',
           'He dropped into a vogue pose at the edge of the dance floor.'),
 'vogue femme': ('It was codified in ballroom as one of the major vogue categories.',
                 'The elements named in the style are used as standard judging criteria.',
                 'Her vogue femme performance had judges leaning forward in their seats.'),
 'duckwalk': ('It is a ballroom dance move that spread to other dance styles.',
              'It appears in many vogue sequences.',
              'The duckwalk down the runway drew cheers from the crowd.'),
 'death drop': ('It is a signature ballroom and vogue move, later seen across drag performance.',
                'It is physically demanding and is taken seriously in competition.',
                'The performance ended with a death drop that shook the front rows.'),
 'serving': ('It is a ballroom and drag term for presenting a strong look.',
             'It implies that the performer is giving the audience something worth watching.',
             'She walked in serving elegance and the whole room noticed.'),
 'kiki': ('In ballroom, a kiki ball is a less formal event, with the kiki scene emerging in the 2000s.',
          'The word also describes a relaxed, gossipy mood.',
          'The kiki ball on Friday was full of first-time walkers.'),
 'legendary': ('It is documented in ballroom cultural histories.',
               'It is an honor given within the community rather than a casual compliment.',
               'He earned legendary status after years of winning categories in several cities.'),
 'shade': ('It was popularized by ballroom and drag culture, with throwing shade and giving shade documented in Paris Is Burning.',
           'It is often misused as a synonym for any insult, but the original idea is indirect disrespect.',
           'She threw shade at the contestant without mentioning her name.'),
 'reading': ('It is described in Paris Is Burning as a ballroom art form, with readings performed in battles.',
             'The term is not a casual synonym for any criticism.',
             'The reading was so precise that the room stopped to listen.'),
 'tea': ('It is commonly linked to Black drag culture, where T can stand for truth.',
         'Spill the tea is now a general phrase for sharing gossip.',
         'She finally spilled the tea about the surprise party.'),
 'slay': ('It is widely used in ballroom and drag and then spread through pop culture in the 2010s.',
          'It can be a short compliment or a challenge.',
          'You slayed that presentation from the first slide.'),
 'snatched': ('It comes from ballroom and drag, where snatched was used for tightly styled looks.',
              'It now extends to hair, makeup, and outfits.',
              'Her outfit was snatched from the earrings down to the shoes.'),
 'ate': ('It is rooted in Black queer and ballroom speech and spread through social media.',
         'The phrase means the performance was so good nothing remains to be said.',
         'He ate that performance and left no crumbs.'),
 'yas': ('It is tied to Black and Latino ballroom speech, with later spread through Drag Race and online fandom.',
         'The elongated spelling signals excitement.',
         'Yasss, that is exactly the outfit for tonight.'),
 'gagging': ('It is used in drag and ballroom culture, with to be gagged meaning stunned.',
             'It can be a compliment or an expression of disbelief.',
             "I'm gagging over how good that choreography looked."),
 'wig': ('It is a ballroom and drag expression adopted widely online, with the phrase my wig meaning shock.',
         'The wig is figurative, and the idea is that excitement removes it.',
         'When the final scene came on, my wig was gone.'),
 "it's giving": ('It is popular in Black queer communities and spread widely in 2021 on social media.',
                 'It is used without a following noun in some jokes, which marks a joking style.',
                 "It's giving old money with that cardigan and tote."),
 'sickening': ('It is used in ballroom and drag as praise.',
               'The word reverses its negative meaning, like several other ballroom terms.',
               'That entrance was sickening in the best possible way.'),
 'hunty': ('The word grew out of ballroom and drag slang as a playful form of honey, and it spread through drag television and social media.',
           'Friends use it affectionately, though it sounds forced when someone uses it to imitate a community they do not know.',
           'Hunty, you have to see what just happened.'),
 'sashay': ('The word has a French origin and was adopted into ballroom and drag vocabulary.',
            'It was boosted by the Drag Race catchphrase sashay away.',
            'She sashayed across the stage with the crowd cheering.'),
 'shantay': ('It comes from the show, which was influenced by ballroom and drag language.',
             'The word is mainly associated with the show rather than general speech.',
             'After the lip sync she heard shantay and burst into tears.'),
 'werk': ('It comes from drag and ballroom, with the spelling reflecting a long drawn-out pronunciation.',
          'It is encouragement more than description.',
          'He stepped onto the floor and the crowd yelled werk.'),
 'purr': ('It is used in ballroom and drag circles before spreading to social media.',
          'It is a short, playful reaction.',
          'When she turned around the audience went purr.'),
 'rizz': ('It was popularized by the streamer Kai Cenat around 2021 and 2022 and named the Oxford Word of the Year in 2023.',
          'It comes from the middle of the word charisma, and its spread shows how streamer vocabulary can reach dictionaries.',
          'He walked up with so much rizz that the whole table went quiet.'),
 'fanum tax': ('It is named for the streamer Fanum, who is part of a creator group that includes Kai Cenat.',
               'It became a widespread joke in 2023 and appears in both spoken and written jokes.',
               "I'm applying the Fanum tax to your fries before you start eating."),
 'gyatt': ('It was popularized by streamers, especially YourRAGE, and said to derive from the exclamation goddamn.',
           'It spread through short-form video in 2023 and is often used ironically by younger users.',
           'He just said gyatt in the middle of the science lesson and the whole class laughed.'),
 'chat': ('It is a standard streaming term used across platforms.',
          'The form of address turns an audience into a character.',
          'Chat, did you see what he just did to that boss fight?'),
 'w in chat': ('It is common on Twitch, YouTube, and Kick chats.',
               'Users often type a stream of W characters to show support.',
               'When the final shot landed, the chat filled with Ws.'),
 'l in chat': ('It is the counterpart to W in chat and is equally widespread across streaming platforms.',
               'It can be teasing or sincere depending on the stream.',
               'The streamer missed the jump, and chat sent a wall of Ls.'),
 'take the l': ('It is an older Black American and hip-hop era phrase that became a gaming staple.',
                'The phrase pairs with take the W.',
                "I'll take the L on that one and pay for lunch."),
 'clip it': ('It is a feature of streaming platforms that creators and chat use to preserve highlights.',
             'It has become a catchphrase that follows any funny moment.',
             'That reaction was so funny that chat shouted clip it.'),
 'bag': ('It is used widely in creator and hip-hop culture, where creators talk about making money.',
         'The phrase suggests focus on career or income.',
         "He's streaming eight hours a day because he wants to secure the bag."),
 "mic'd up": ('It is a sports and music term adopted by streamers.',
              'It implies that the unfiltered moment is part of the entertainment.',
              "The coach was mic'd up, and the fans got every word of the pep talk."),
 'lobby': ('It is a standard gaming term, and in console shooters the lobby became a social space for trash talk and joking.',
           "It is the setting for much of the community's humor.",
           'Half the fun of the night was talking in the lobby before the match.'),
 'run it back': ('It is a phrase from sports and competitive gaming popular in Black fighting game and sports game communities.',
                 'It signals confidence and a willingness to continue.',
                 "That last round was close, so let's run it back."),
 'light work': ('It is a hip-hop and sports expression adopted widely in gaming.',
                'It can be modest praise or a boast.',
                'That boss was light work after we found the weak point.'),
 'clapped': ("It is a gaming term that comes from the sound of clapping or from clapping someone's cheeks, with a general meaning of being beaten.",
             'It is casual and can be self-deprecating.',
             'I got clapped in the first round and had to wait for the next bracket.'),
 'cooked': ('It is popular on gaming and meme culture, and also used for exceptional performance, as in he cooked.',
            'The double meaning shows how context decides whether the word is praise or defeat.',
            "If the final boss has a second phase, we're cooked."),
 'cracked': ('The word is gaming slang for a player who is performing at a very high level.',
             'The word can be admiring or suspicious.',
             'That kid is cracked at this game, and he is only twelve.'),
 'sweaty': ('It comes from sweat, referencing the physical effort of a tryhard player.',
            'It is often used as a gentle complaint about opponents who take casual matches too seriously.',
            'Every lobby tonight was sweaty, so we switched to a private match.'),
 'tryhard': ('It is long used in gaming and school culture.',
             'It can be an insult or a compliment.',
             "He's a tryhard in every single match, even the practice games."),
 'cheese': ('It is common across fighting games and online matches.',
            'It often provokes complaints, though some communities embrace it.',
            'He cheesed the final round by repeating the same attack.'),
 'salty runback': ('It is a standard term in the fighting game community.',
                   'The phrase became a community meme.',
                   'After the loss, he asked for a salty runback right away.'),
 'scrub': ("It is defined in David Sirlin's essay series Playing to Win, which the FGC adopted in the 2000s.",
           'The term is more specific than its ordinary meaning of an unimportant person.',
           'He kept calling the other player cheap, which is classic scrub behavior.'),
 'money match': ('It is used in fighting game and 2K culture.',
                 'It signals a high-stakes friendly game.',
                 'They set up a money match at the arcade after the tournament ended.'),
 'pocket': ('It is an FGC term for a surprise choice.', 'It adds drama to a tournament.', 'He saved his pocket character for the final round.'),
 'the park': ('It is a feature of NBA 2K since the 2010s.',
              'It grew into a community with its own slang and rivalries.',
              "After school he'd log into the Park and run a few games."),
 'pro-am': ("It is an organized part of the game's competitive community.",
            'The term borrows from professional and amateur golf.',
            'Our squad is practicing for the next Pro-Am season.'),
 'green': ('It is a fan and developer term for the highest-quality shot release.',
           'Green is shorthand for perfect timing in the game.',
           'He kept getting green releases from the corner.'),
 'badges': ('It is an official game feature that players discuss at length.',
            'The discussions use their own vocabulary.',
            'He spent a week grinding for the badge he wanted.'),
 'dub': ('The term comes from the letter W for win and appears in sports talk and gaming chat since at least the 2010s.',
         'Players say take the dub when they want to claim a win and often type W in streams to celebrate.',
         'We got the dub in overtime.'),
 'gg': ('It is a gaming courtesy phrase with roots in early online game culture.',
        'When used sarcastically, as in gg ez, it becomes taunting.',
        'We said gg after the match and agreed to a rematch.'),
 'gg ez': ('It is a toxic variant of gg that became widespread in games like League of Legends.',
           'It is widely considered poor sportsmanship.',
           'The other team typed gg ez, so we muted the chat.'),
 'lag': ("The word comes from networking vocabulary and describes the delay between a player's input and the game's response.",
         'Gamers often blame lag for losses, which has turned the word into a running joke about excuses.',
         'I would have won, but the lag made me miss the dodge.'),
 'ping': ('It is a network term that became standard in gaming.',
          'Low ping is considered ideal.',
          'His ping spiked to three hundred right when the match started.'),
 'carry': ('It is a Southern and Gullah-linked sense of carry.',
           'It differs from the standard meaning of physically bearing something.',
           'He offered to carry me to the station.'),
 'clutch': ('It is borrowed from sports and used across competitive gaming.',
            'The word suggests nerves and skill.',
            'He hit the clutch play with two seconds left.'),
 'tilt': ('It is borrowed from poker and used widely in gaming.',
          'Players warn each other not to go on tilt.',
          'After three losses in a row, he was on tilt.'),
 'mid': ('It spread through gaming and social media in the 2020s.',
         'It is used for characters, items, and people.',
         'That new character looks mid compared with the old one.'),
 "y'all": ('It is a long-standing feature of Southern American English, shared by Black and white Southern speakers.',
           "The form is now widespread across the country, and its related forms include all y'all for emphasis.",
           "Y'all are welcome to come over after the game."),
 "all y'all": ('It is recorded in Southern English as a way to stress that everyone is included.',
               'It signals warmth and inclusion.',
               "I want all y'all to pick a plate before the food goes cold."),
 "fixin' to": ('It is a Southern American construction that is the source of finna.',
               'It is often used in friendly conversation.',
               "I'm fixin' to leave for church if you want a ride."),
 'might could': ('It is a feature of Southern American English and of Scots-Irish dialect heritage.',
                 'It is considered a distinctive Southern marker.',
                 'We might could finish the quilt by Sunday.'),
 'bless your heart': ('It is a Southern idiom whose meaning depends heavily on voice and situation.',
                      'It has become famous nationally as a joke about the difference between sincere and sarcastic uses.',
                      'He tried to fix the sink himself, bless his heart.'),
 'reckon': ('It is an older English verb that remains common in Southern and Appalachian speech.',
            'It appears in everyday conversation as a soft way to say I think.',
            "I reckon it's going to rain before supper."),
 'yonder': ('It is an old English word preserved in Southern and Appalachian speech.',
            'It often implies a place within sight.',
            'The barn is right over yonder past the fence.'),
 'coke': ('It is a recognized regional usage in the South, with surveys showing it scattered through the region.',
          'The term illustrates a classic dialect map difference alongside pop and soda.',
          'He asked what kind of coke I wanted, and I said Dr Pepper.'),
 'buggy': ('It is a regional word used in parts of the South.',
           'It is the kind of local noun that shows up in dialect surveys.',
           'Grab a buggy and meet me at the produce section.'),
 'holler': ('It is a Southern and Appalachian term derived from hollow, with the shout meaning recorded across many dialects.',
            'The two meanings coexist in the same regions.',
            'He grew up in a holler where everyone knew the neighbors.'),
 'dadgum': ('It is a Southern speech habit of softening profanity.',
            'It appears in friendly or comedic speech.',
            "That dadgum car won't start again."),
 'cattywampus': ('It is a Southern and Midwestern regional word with several spellings.',
                 'It is often mentioned in lists of colorful regional vocabulary.',
                 'The picture frame is cattywampus on the wall.'),
 'supper': ('It is a regional pattern in Southern and rural speech.',
            'The difference between supper and dinner often depends on family tradition.',
            'We eat supper at six, after the chores are done.'),
 'directly': ('It is a Southern usage that differs from the standard meaning of immediately.',
              'The time sense can confuse outsiders.',
              "I'll be there directly, after I finish this call."),
 'mash': ('It is a Southern and Appalachian usage.',
          'It applies to elevators and doorbells.',
          'Mash the elevator button, since it never responds the first time.'),
 'hissy fit': ('It is a Southern expression that is now widely used.', 'It carries a teasing tone.', 'He threw a hissy fit when the printer jammed.'),
 'fit to be tied': ('The expression draws on the old image of a person so enraged that restraints would be needed, and it remains common in Southern '
                    'conversation.',
                    'It is mostly used humorously, to describe fury that is bigger than the situation deserves.',
                    'She was fit to be tied when she heard the news.'),
 'sugar': ("It is a Southern habit of warm address, along with honey and darlin'.",
           'It is gentle and friendly in most settings, though some find it patronizing from strangers.',
           'Thanks for waiting, sugar, your order will be right up.'),
 "ma'am": ('It is a long Southern tradition that is taught as respect.',
           'The practice is often a cultural expectation for children.',
           "Yes, sir, I'll have it ready by morning."),
 'pert near': ('It is a Southern and Appalachian contraction of pretty near.',
               'It appears in rural speech.',
               'He pert near finished the whole pie by himself.'),
 'plumb': ('It is a regional intensifier in Appalachian and Southern speech.',
           'It often modifies adjectives of exhaustion.',
           "I'm plumb worn out from the day's work."),
 'right smart': ('It is an Appalachian and Southern phrase.',
                 'It can describe distance, time, or quantity.',
                 "It's a right smart walk from the road to the creek."),
 'poke': ('It is an old English word surviving in Appalachian speech and in the saying a pig in a poke.',
          'The word shows how regional dialects preserve older vocabulary.',
          'She carried the apples home in a poke.'),
 'tote': ('It is a regional verb, with possible African and Southern roots discussed by scholars.',
          'The word is widely used in the South.',
          'He totes water up the hill every morning.'),
 'sigogglin': ('It is an Appalachian dialect word with several spellings.',
               'It is recorded in regional dictionaries.',
               'The fence post was sigogglin after the storm.'),
 "young'uns": ('The word is a contraction of young ones and is common in Southern and Appalachian speech.',
               'Older speakers use it fondly, and younger speakers may use it playfully in imitation.',
               "The young'uns are playing out in the yard."),
 "fair to middlin'": ('It is an old rural English idiom common in Southern and Appalachian conversation.',
                      'It is a modest answer to how are you.',
                      "How's the crop? Fair to middlin' this year."),
 'ope': ('It is a Midwestern interjection often joked about nationally.',
         'It carries a polite, apologetic tone.',
         'Ope, let me just squeeze past you here.'),
 'pop': ('It is the dominant term across much of the Midwest and the West.',
         'Dialect maps show pop, soda, and coke as regional alternatives.',
         "I'll grab a pop from the cooler on the way out."),
 'uff da': ('It was brought by Norwegian American immigrants, with strong ties to Minnesota and Wisconsin.',
            'It is a gentle expression, not a curse.',
            'Uff da, that was a lot of snow overnight.'),
 'hotdish': ('It is a Minnesota term associated with church suppers and Scandinavian American communities.',
             'The word is a cultural marker for the state.',
             'She brought a tater tot hotdish to the potluck.'),
 'you betcha': ('It is a Midwestern, especially Minnesotan and Dakota, expression boosted by pop culture.',
                'The phrase is often exaggerated in jokes.',
                'Are you coming Saturday? You betcha.'),
 'dontcha know': ('It is associated with Upper Midwest speech.',
                  'Outsiders often exaggerate it in imitation.',
                  "It's going to be a cold one tonight, dontcha know."),
 'yooper': ('The name comes from the initials UP for Upper Peninsula, which gave rise to a recognizable regional identity and accent.',
            'Yoopers use the label with pride, and the dialect has features influenced by Finnish, Cornish, and other immigrant languages.',
            "He's a proud Yooper and he never goes anywhere without a warm coat."),
 'bubbler': ('It is used in Wisconsin and in parts of New England, with a trademark history in Wisconsin.',
             'It is a classic example of a regional noun.',
             'She stopped for a drink at the bubbler.'),
 'stop and go light': ('It is a regional term used in parts of the Midwest.',
                       'It appears in dialect surveys.',
                       'Turn left at the stop and go light by the gas station.'),
 'the cities': ('It is a regional shorthand in Minnesota.',
                'It shows how local geography shapes speech.',
                "We're driving to the cities for the weekend."),
 'up north': ('It is a Midwestern cultural idea, particularly in Michigan and Wisconsin.',
              'It refers to a lifestyle and place as well as a direction.',
              'They have a cabin up north that the whole family uses in summer.'),
 'minnesota nice': ('It is a cultural label used by residents and outsiders.',
                    'It can describe real friendliness or a passive way of avoiding conflict.',
                    'She said that might be a challenge, which in Minnesota nice meant no.'),
 'supper club': ('Supper clubs in Wisconsin grew out of mid-twentieth-century roadside restaurants and became known for relish trays, old fashioned '
                 'cocktails, and Friday fish fry.',
                 'The phrase signals a specific kind of leisurely social meal rather than a membership club.',
                 'We went to the supper club for the Friday fish fry.'),
 'wicked': ('It is associated with New England, especially Massachusetts and Boston.',
            'It is a classic regional intensifier.',
            'That clam chowder was wicked good.'),
 'packie': ('The word is short for package store and is a mark of New England speech, especially in Massachusetts.',
            'Visitors may not recognize it, since other regions say liquor store or bottle shop.',
            'We stopped at the packie before the party.'),
 'frappe': ('It is a Massachusetts and eastern New England term.',
            'Outsiders may confuse it with the coffee drink.',
            'He ordered a chocolate frappe with extra whipped cream.'),
 'jimmies': ('It is a term common in Boston and parts of New England.',
             'The word is the subject of friendly regional debates.',
             'She put rainbow jimmies on the ice cream cone.'),
 'rotary': ('It is used in New England, especially Massachusetts.',
            'The term is a local alternative to roundabout.',
            'Take the second exit at the rotary.'),
 'the t': ("The Massachusetts Bay Transportation Authority's subway and rail system is known to locals simply as the T, after its logo.",
           'Using the nickname signals familiarity with Boston and avoids sounding like a tourist.',
           'I took the T to the game and it was packed.'),
 'bodega': ('It is a New York usage, borrowed from Spanish and tied to Latino shopkeepers.',
            'The word also carries cultural and community meaning.',
            'He grabbed a coffee and a bacon egg and cheese from the bodega.'),
 'stoop': ('It is a New York and mid-Atlantic term of Dutch origin.',
           'It is a social space in city neighborhoods.',
           'The neighbors sat on the stoop and watched the street.'),
 'on line': ('It is a New York City usage, where other regions say in line.',
             'The preposition is a distinct regional marker.',
             'We waited on line for an hour to get the sandwich.'),
 'regular coffee': ('It is a New York and Boston expression, especially in delis.',
                    'The term shows how local habits can redefine a plain word.',
                    'He asked for a regular coffee and a roll.'),
 'youse': ('It is found in Philadelphia, New York, and some other Northeastern dialects, with Irish and Italian immigrant influence.',
           'It fills the gap left by the lack of a distinct plural you in standard English.',
           'Youse should come over for dinner on Sunday.'),
 'jagoff': ('It is associated with Pittsburgh, with roots in Scots-Irish and Pennsylvania German speech.',
            'It carries a mildly vulgar tone.',
            'That jagoff cut me off in the parking lot.'),
 'yinz': ('It is a contraction of you ones, tied to Scots-Irish settlers.',
          'It is a strong marker of local identity.',
          'Yinz coming to the game this weekend?'),
 'nebby': ('The word is a dialect form probably derived from neb, an old word for nose, and is associated with Pittsburgh and western Pennsylvania.',
           'It can be a gentle description of a curious neighbor or a pointed criticism of someone who pries.',
           'The neighbor is nebby but she means well.'),
 "n'at": ('It is a Pittsburgh phrase showing a trailing off.', 'It is a cultural marker.', "We had some pierogies and kielbasa n'at."),
 'redd up': ('It is a Pittsburgh and Pennsylvania Dutch influenced phrase.',
             'It is a clear regionalism.',
             'I need to redd up the living room before they arrive.'),
 'gumband': ('The word is a regional name for a rubber band, associated with Pittsburgh and Pennsylvania speech.',
             'It surprises outsiders because rubber band seems like the only name for the object.',
             'Hand me a gumband for these papers.'),
 'down the shore': ('It is a Philadelphia and New Jersey phrase, where down is used instead of to.',
                    'The preposition marks local speech.',
                    "We're going down the shore for the weekend."),
 'hon': ('It is strongly associated with Baltimore working-class culture.',
         'The term is affectionate, and a local festival celebrates it.',
         'Can I get you some coffee, hon?'),
 'hoagie': ('It is a Philadelphia term, with regional variants across the Northeast.',
            'Dialect maps use the sandwich as a classic example.',
            'We picked up a hoagie for lunch.'),
 'gnarly': ('It was popularized in California surf and skate culture in the 1970s.',
            'The sense has shifted over time and now reads as retro.',
            'That wave was gnarly, and we all knew it.'),
 'stoked': ('It is associated with surf culture, with the word spreading through California.',
            'It is a casual emotional word.',
            "I'm so stoked for the trip this weekend."),
 'rad': ('It is short for radical, popularized in California skate and surf culture in the 1980s.',
         'It is often used nostalgically.',
         "That skate park is rad, and it's free."),
 'the 5 and the 405': ('It is a distinct regional habit that outsiders find odd.',
                       'Northern California speakers use the practice less.',
                       'I got stuck on the 405 for an hour.'),
 'hecka': ('It is used in Northern California and associated with the Sacramento and Bay Area region.',
           'It is lighter and more playful than the original.',
           'There was hecka traffic on the bridge.'),
 'janky': ('The term is commonly linked to African American speech in the Bay Area, and it spread through hip-hop and California youth slang.',
           'People use it for objects and situations that are shaky, shoddy, or not to be trusted.',
           'The elevator is so janky I take the stairs.'),
 'gag me with a spoon': ('It is associated with the Valley Girl era and a hit song of 1982.',
                         'The phrase is now mostly retro.',
                         'That cafeteria food is so bad, gag me with a spoon.'),
 'bogus': ('It is popular in California youth speech of the 1980s.', 'It is now mostly nostalgic.', 'That call from the referee was totally bogus.'),
 'shred': ('It is an action-sports term adopted from surf and skate culture.',
           'It can also describe playing guitar fast.',
           'They went up to the mountain to shred all day.'),
 'send it': ('It is a term from snowboarding, skiing, and mountain biking, which spread to general casual speech.',
             'It can encourage bravery or bad decisions.',
             'The ramp looked huge, but he said just send it.'),
 'kook': ('The word comes from surf culture, where it names a beginner who behaves as if they were an expert.',
          'Surfers use it sharply, so being called a kook in the water is an insult about attitude as much as skill.',
          'He wore all the gear but looked like a kook on the first wave.'),
 'grom': ('It is a short form of grommet, used in surf culture.',
          'The word often carries affection.',
          'The groms were out early, practicing their turns.'),
 'the mountain is out': ('It is a cultural phrase in the Pacific Northwest.',
                         'It is a statement about the weather and a mood.',
                         "It's a sunny day, so the mountain is out."),
 'seattle freeze': ('It is a cultural idea shared by residents and newcomers.',
                    'It is a stereotype with some truth for many newcomers.',
                    'She said the Seattle freeze made it hard to make friends at first.'),
 'dank': ('The word began as an old term for damp and cold, and it later became praise in cannabis slang and then in internet meme culture.',
          'The word has two quite different uses.',
          'The sandwich was dank and so was the playlist.'),
 'bro': ('It is associated with fraternity and sports culture and spread widely in the 2000s.',
         'Its use for people of all genders has increased.',
         'Bro, you will not believe what happened in lab today.'),
 'dude': ('It is originally a nineteenth-century word for a fashionable man, later reshaped by California surf and skate culture.',
          'Linguists describe it as a flexible solidarity marker.',
          "Dude, that was the best sandwich I've ever had."),
 'chad': ('It was popularized in internet culture in the 2010s.',
          'The term can be a compliment or an insult.',
          'The guy at the gym was a total Chad with an impressive routine.'),
 'ollie': ('It is named for skater Alan Ollie Gelfand, who developed it in the late 1970s.',
           'The word is the foundation of most street skateboarding.',
           'He finally landed his first ollie over the curb.'),
 'kickflip': ('The trick was developed by skaters in the 1980s, with skater Rodney Mullen often credited for pioneering the modern flatground '
              'version.',
              'It is one of the first tricks that many learners work toward, and landing one is a rite of passage.',
              'She spent the afternoon practicing her kickflip.'),
 'bail': ('It is used in skateboarding and general slang.',
          'The meaning has expanded to include leaving a plan.',
          'He bailed on the trick just before landing.'),
 'emo': ('It began in the 1980s hardcore scene and grew in the 2000s.',
         'The word can describe a style or a mood.',
         'She had an emo phase with studded belts and long bangs.'),
 'scene kid': ('The subculture emerged in the mid-2000s from emo and hardcore scenes and was shaped by MySpace, with bright colors and distinctive '
               'hair.',
               'The term is mostly nostalgic now, though it can still describe someone who dressed in that style as a teenager.',
               'He was a scene kid in high school with brightly dyed hair.'),
 'goth': ('The subculture began in the early 1980s in Britain, shaped by post-punk bands such as Bauhaus and Siouxsie and the Banshees.',
          'Goth fans often object to casual use of the word as a costume label for anyone who wears black.',
          'The goth club had a night with only classic songs.'),
 'normie': ('It is used on internet forums and spread to wider culture.',
            'It can be playful or derisive.',
            "He's a total normie who only watches mainstream shows."),
 'theater kid': ('It is a school social label that became a meme in the 2020s.',
                 'It can be affectionate or teasing.',
                 'She burst into song in the hallway because she is a theater kid.'),
 'redneck': ('It is historically derogatory but reclaimed by many rural people.',
             'The word is potentially offensive from outsiders.',
             'He wore the label redneck with pride on the back of his truck.'),
 "good ol' boy": ('It is a Southern phrase with affectionate and critical senses.',
                  'It can also refer to political favoritism.',
                  "He's a good ol' boy who knows everyone in the county."),
 'hold my beer': ('It is a joke format from American rural humor.',
                  'The phrase became a meme introducing reckless actions.',
                  "Hold my beer, I'm going to jump the creek."),
 'tailgate': ('It is an American sports and country culture tradition.',
              'The word has also become a verb.',
              'We tailgated for four hours before kickoff.'),
 'touch grass': ('It is an internet insult aimed at people seen as too online.',
                 'It can be a joke or a pointed criticism.',
                 "You've been arguing in the comments all day, so go touch grass."),
 'chronically online': ('It is an online insult that spread in the late 2010s.',
                        'It is often used between internet users who are themselves online a lot.',
                        'His take is so chronically online that nobody offline would understand it.'),
 'doomscrolling': ('It was popularized during the 2020 pandemic.',
                   'The word was widely discussed in media and dictionaries.',
                   'I stayed up doomscrolling instead of sleeping.'),
 'cringe': ('The word has been in popular use since the 2010s, though it appears earlier in other senses.',
            'The term can be applied to people, content, or oneself.',
            'His old posts are painful and so cringe.'),
 'cope': ('It comes from internet forum culture where cope and seethe became a mocking pair.',
          'It is typically used in arguments.',
          "That's just cope, since the results speak for themselves."),
 'seethe': ('It appears in forum insults as the second half of the pair cope and seethe, which mocks both denial and anger.',
            "The word is meant to belittle an opponent's reaction, so using it usually escalates an argument.",
            'Cope and seethe about the final score.'),
 'npc': ('It is used as an insult in internet culture.',
         'It has been used in political and social debates.',
         'The crowd all repeated the same line like NPCs.'),
 'main character energy': ('It is a social media phrase of the 2020s that grew from the idea of main character syndrome.',
                           'It can be a compliment or a joke.',
                           'She walked down the street with so much main character energy.'),
 'delulu': ('It was popularized by K-pop fandom spaces and then spread widely.',
            'It began as fan slang.',
            "I'm delulu enough to believe the tickets will still be available."),
 'ick': ('The use dates to the television show Ally McBeal, and it became a social media staple in 2021.',
         'It is used for a small detail that ends interest.',
         'He chewed with his mouth open and gave me the ick.'),
 'situationship': ('The word blends situation and relationship and became common in dating conversation in the 2010s.',
                   'It names a relationship that lacks a label, which is why many people say it with a mix of humor and frustration.',
                   "We've been in a situationship for months with no clear label."),
 'red flag': ('It is a general metaphor that grew in popularity in dating conversations.',
              'Its counterpart is green flag.',
              'Canceling plans every week is a red flag.'),
 'green flag': ('It is the positive counterpart to red flag and became popular in the same dating conversations.',
                'It is used for healthy habits.',
                'He remembered my allergies, which is a green flag.'),
 'gaslight gatekeep girlboss': ('It is a meme from the early 2020s.',
                                'It mocks both corporate feminism and psychological terms.',
                                'She said gaslight gatekeep girlboss while closing the laptop.'),
 'side quest': ('It is used widely in the 2020s.', 'It reframes errands as adventures.', 'Grabbing coffee turned into a side quest across town.'),
 'lore': ('It comes from video game and fantasy terms and widely used in social media.',
          'It can mean personal history.',
          'He has so much lore from his college years.'),
 'era': ('It was popularized in the 2020s, with the Taylor Swift Eras Tour contributing.',
         'It frames personal change as a chapter.',
         "I'm in my study era, so I can't go out tonight."),
 'core': ('It grew from internet aesthetics communities in the 2010s.',
          'The suffix is applied to many styles.',
          'Her room is pure cottagecore with plants and soft lamps.'),
 'vibe check': ('It spread through social media in the 2010s.',
                'It can be literal or jokingly formal.',
                'The new apartment passed the vibe check immediately.'),
 'brainrot': ('It is named the 2024 Oxford Word of the Year.',
              'It is used by critics and enthusiasts alike.',
              'He watches so many absurd clips that his brainrot is obvious.'),
 'skibidi': ('It was created by Alexey Gerasimov and popularized from 2023.',
             'The word is mostly used as a joke.',
             'The kids shouted skibidi as a nonsense word during recess.'),
 'sigma': ('It comes from manosphere vocabulary, later used ironically by Gen Alpha.',
           'Most of its current use is satirical.',
           'He claimed to be sigma while eating lunch alone.'),
 'ohio': ('It is an internet joke that took off in the 2020s.', 'It is not meant literally.', 'That cashier sang at the register, which is so Ohio.'),
 'mewing': ('It is named after British orthodontist Mike Mew, and popularized on social media in 2023.',
            'It is more of a meme than a proven technique.',
            'He kept mewing during the entire class photo.'),
 'looksmaxxing': ('It comes from online forums and then spread to short-form video.',
                  'It can describe harmless grooming or extreme practices.',
                  'He started looksmaxxing with a new haircut and skincare routine.'),
 'aura': ('It is a meme that spread in 2024, framing actions as gaining or losing aura points.',
          'It is both a joke and a social scorekeeping game.',
          'He lost a thousand aura when he tripped on the stage.'),
 'aura farming': ('It was popularized in 2025 and tied to viral clips of confident behavior.',
                  'It is often used ironically.',
                  'He was aura farming in the hallway with sunglasses on.'),
 'six seven': ('It is widely reported in 2025 as a defining youth meme, tied to a rap song and to basketball player LaMelo Ball, who is six feet '
               'seven inches tall.',
               'Adults often find it baffling, which is part of its appeal.',
               'The students all yelled six seven when the teacher said the page number.'),
 'crash out': ('It was popularized in Black social media in the 2020s and then spread widely.',
               'It can describe an outburst or a bad choice.',
               'He crashed out and quit the group chat.'),
 'locked in': ('The phrase borrows from sports and hip-hop talk about being fully focused, and it surged on social media in 2024 and 2025.',
               'Users post it as a caption for study sessions, workouts, and big projects to signal that distractions are off the table.',
               "I'm locked in until finals are over."),
 'clanker': ('It is borrowed from a Star Wars universe insult for droids.',
             'Some critics note it echoes the form of slurs, so its use is debated.',
             'He called the chatbot a clanker after it failed the task.'),
 'mogging': ('The term comes from looksmaxxing forums, where mogging means outshining another person in appearance.',
             'Many people use it ironically in short videos, and critics worry that the forums behind it promote unhealthy beauty obsessions.',
             'He kept mogging everyone in the group photo.'),
 'based': ('It is associated with rapper Lil B, who popularized based in the 2000s.',
           'The word later gained a different meaning in political internet culture.',
           'Her answer was totally based, and everyone clapped.'),
 'stan': ('It is named after the 2000 Eminem song Stan.', 'The word is now used as both noun and verb.', 'I stan that band and own all the albums.'),
 'ratio': ('The practice began on Twitter, where a reply with more likes than the original post was taken as proof that the poster was wrong.',
           'The word became a joke, and users sometimes reply with the single word ratio to claim a victory.',
           'His take got ratioed within minutes.'),
 'rent free': ('It is a social media phrase that grew in the late 2010s.',
               'It is used mockingly and affectionately.',
               'That song lives in my head rent free.'),
 'yapping': ('It is a Gen Z and Gen Alpha term used for long conversations.',
             'It can be affectionate or critical.',
             "She's been yapping about her trip for an hour."),
 'rage bait': ('It is named Oxford Word of the Year in 2025.',
               'It describes a common online strategy.',
               'The video was pure rage bait, built to fill the comments with arguments.'),
 'unalive': ('It is an algospeak term that spread on TikTok in the early 2020s.',
             'Mental health professionals have raised concerns that it can soften serious subjects.',
             'The video used unalive as a replacement word because the platform flags the real term.'),
 'seggs': ('It is an internet alteration that spread in the late 2010s and 2020s.',
           'It signals both humor and caution.',
           'The health class had a lesson on seggs education.'),
 'le dollar bean': ('It is an algospeak phrase from TikTok.',
                    'Creators use it so that content is not suppressed.',
                    'The creator posted a video about le dollar bean pride.'),
 'corn': ('It is an algospeak spelling and emoji tactic.',
          'The emoji of corn is also used.',
          'He used the corn emoji instead of the actual word to avoid the filter.'),
 'órale': ('It is widely used in Mexican Spanish and carried into Chicano speech in California and the Southwest.',
           'The exact meaning depends on tone, so the same word can cheer someone on or express surprise.',
           "Órale, I'll meet you at the corner in five minutes."),
 'ese': ('It is a Chicano English and Caló form derived from the Spanish demonstrative meaning that one.',
         'Films and television have turned it into a stereotype, so outsiders using it often sound like parody.',
         'Hey, ese, thanks for helping me move the couch.'),
 'vato': ('The word comes from Caló and spread through Chicano and Mexican American speech in the twentieth century.',
          'Among friends it is neutral, though its older association with street life gives it a rougher edge in some contexts.',
          'That vato at the corner shop always saves me a seat.'),
 'carnal': ('It is a Mexican and Chicano term that borrows the language of blood relatives for friendship.',
            'Calling someone carnal signals deep trust, so it is not used lightly with new acquaintances.',
            "He's my carnal, so I trust him with my keys."),
 'chale': ('It is a Mexican exclamation that Chicano speakers carry into English conversation.',
           'The vowel is often stretched to show how disappointed the speaker feels.',
           'Chale, I forgot my wallet at home.'),
 'no manches': ('It began as a softened replacement for a much more vulgar phrase and became acceptable on Mexican television.',
                'The polite substitute shows how Spanish speakers soften strong expressions without losing their punch.',
                'No manches, you finished the whole project in one night?'),
 'chido': ('This Mexican slang word is used across the country, and the phrase qué chido expresses admiration.',
           "Some speakers in other Spanish-speaking countries find it distinctly Mexican, so it can mark the speaker's origin.",
           'The party was so chido that nobody wanted to leave.'),
 'neta': ('It is Mexican slang that appears both as a question, neta, meaning really, and as an affirmation.',
          'The word is nearly untranslatable because it works as both a noun and a discourse marker.',
          'Neta, I thought the concert started at seven.'),
 'güey': ('It grew from the word for ox, which was once an insult, and now serves as a casual form of address.',
          'Using it with an elder or a stranger can sound rude, so the setting matters.',
          'Wey, did you see the game last night?'),
 'simón': ('This Mexican slang form is a playful alteration of the word for yes.',
           'It is mostly used among younger speakers and sounds out of place in formal conversation.',
           "Simón, I'm in for the trip on Saturday."),
 'ahorita': ('It is the diminutive of ahora, and its time meaning stretches depending on the speaker and the situation.',
             'The ambiguity is a well-known running joke among Mexican and Mexican American families.',
             'Ahorita voy, which might mean in two minutes or in two hours.'),
 'fresa': ('The word literally means strawberry and entered Mexican slang as a label for status and attitude.',
           'It can be playful teasing or a real criticism of snobbery.',
           'He talks like a total fresa, with brand names in every sentence.'),
 'naco': ('It is used in Mexican Spanish with clear classist overtones.',
          'Many Mexicans reject the word because it ranks people by class, though some reclaim it ironically.',
          'The word naco is rejected by many people because it judges others by class.'),
 'chamba': ('The word is a Mexican colloquialism for work that spread widely in Chicano speech, with chambear meaning to work.',
            'It sounds more casual than the standard word for work and often refers to odd jobs or hustles.',
            'I picked up some extra chamba this week at the warehouse.'),
 'chamaco': ('This is a Mexican term, and the feminine form is chamaca.',
             'It is affectionate when used by family and neighbors.',
             'The chamacos are playing outside until dinner.'),
 'morro': ('It is a regional word from northern Mexican Spanish, and the feminine form is morra.',
           'People from central Mexico may use chavo or chamaco for the same idea.',
           'The morros ran down the street laughing.'),
 'chavo': ('It is common in central Mexico and was popularized by the television character El Chavo del Ocho.',
           'The feminine form chava is used for a girl or young woman.',
           'That chavo works at the shop on the corner.'),
 'pinche': ('This Mexican and Chicano word started as a term for a kitchen helper and became a general expletive.',
            'It is common in everyday speech but impolite in formal settings.',
            "It's a pinche scorching day, and the air conditioning is broken."),
 'chisme': ('The Spanish word spread widely into English among Latino speakers, and chismoso is the word for a gossip.',
            'Many bilingual speakers use it in English sentences because there is no equally vivid English equivalent.',
            'She came over with the latest chisme about the neighbors.'),
 'ni modo': ('It is a Mexican phrase of acceptance that literally means no way.',
             'It is a gentle way to accept a setback without drama.',
             "We missed the bus, ni modo, we'll walk."),
 'aguas': ('The Mexican warning literally means waters and is thought to come from the old custom of shouting before throwing dirty water from '
           'windows.',
           'It is shouted as a quick alert in streets, kitchens, and playgrounds.',
           'Aguas, the floor is wet!'),
 'ándale': ('This Mexican interjection became familiar to English speakers through cartoon characters.',
            "The cartoons' exaggerated accents mean that some Mexican Americans find outsider use grating.",
            'Ándale, the movie is about to start.'),
 'híjole': ('It is a mild Mexican interjection believed to be a softened form of a stronger expression.',
            'It suits polite settings and appears in family conversation.',
            'Híjole, that was a close call.'),
 'qué onda': ('It is a widely used Mexican greeting that spread through music and film.',
              'The response is often nada, meaning nothing much, or a longer reply.',
              'Qué onda, are you coming to the market?'),
 'buena onda': ('It is a Mexican phrase, and mala onda is the opposite.',
                'It describes both people and situations.',
                "He's buena onda and always makes everybody comfortable."),
 'padre': ('In Mexican slang the word for father also works as an adjective of approval, as in qué padre.',
           'It is a good example of how a family word can turn into slang.',
           'The new skate park is padre.'),
 'gacho': ('It is a Mexican slang adjective with uncertain origins.',
           'People use it to criticize behavior as well as objects.',
           'That was a gacho thing to say to your friend.'),
 'chafa': ('This Mexican slang word describes cheap or poorly made goods.',
           'It is often used for knockoffs and flimsy products.',
           'The phone case I bought was chafa and broke in a week.'),
 'lana': ('Mexican speakers use lana alongside feria and varo as informal words for cash.',
          'The wool comparison dates from older days when wool was a trade good.',
          "I don't have the lana for a concert this month."),
 'feria': ('In Mexican Spanish the word can mean coins, as in asking for the feria.',
           'It is a casual way of referring to pocket money.',
           'I only have a bit of feria in my pocket.'),
 'chela': ('This Mexican slang word is common in casual settings, and the diminutive chelita is also heard.',
           'It is mostly used by adults among friends.',
           'We grabbed a couple of chelas after the game.'),
 'chilango': ('The word is used inside and outside the city and has an uncertain origin.',
              'People from other parts of Mexico may use it with mild mockery, while Mexico City residents often claim it with pride.',
              'The chilango on my team always knows the best taquerias.'),
 'pocho': ('The term is used within Mexican and Chicano communities and can criticize cultural distance.',
           'It is potentially offensive from outsiders, although some speakers reclaim it with humor.',
           'He called himself pocho with a laugh, and no one corrected him.'),
 'chicano': ('It was once used as a derogatory label before activists adopted it as a symbol of pride.',
             'The word carries political and generational meaning, and not all Mexican Americans use it.',
             'He proudly said that he was Chicano and that his grandfather came to the fields.'),
 'latinx': ('Latinx emerged in the 2000s in online and academic circles, and Latine is a form that fits Spanish pronunciation.',
            'Surveys, including Pew Research from 2019 and 2020, found that only a small share of Hispanic adults use Latinx, so the term is '
            'contested.',
            'The student group changed its name to Latine Student Union.'),
 'jefa': ('These terms are used in Mexican and Chicano family speech.',
          'They are affectionate rather than disrespectful, and they often appear in song lyrics and social media captions.',
          'My jefa packed lunch for everyone this morning.'),
 'mija': ('They are contractions of mi hija and mi hijo.',
          'Speakers also use them with younger friends and neighbors who are not family.',
          'Mija, come eat before the food gets cold.'),
 'trucha': ('The Mexican word literally means trout and in slang means someone sharp or a warning to pay attention.',
            'The shouted form is a quick alert like aguas.',
            'Trucha, someone is coming around the corner.'),
 'ruca': ('It comes from Caló and appears in older Chicano speech.',
          'Younger speakers may find it dated.',
          'He brought his ruca to the family barbecue.'),
 'ranfla': ('The word comes from Caló and is closely associated with lowrider culture in the Southwest.',
            'A car is often a symbol of family and neighborhood pride.',
            'His ranfla gleamed under the streetlights.'),
 'firme': ('It is Chicano slang and is also used to mean agreed.',
           'The word signals approval and calm confidence.',
           'Everything is firme, nothing to worry about.'),
 'cholo': ('It is historically the words were used as derogatory labels, then adopted and reclaimed by some in the community.',
           'The terms are potentially offensive, and the style should not be used as a costume.',
           'The art show featured a photographer who documented chola style in the 1990s.'),
 'pachuco': ('The subculture is tied to the 1943 Zoot Suit Riots in Los Angeles.',
             'It is mainly a historical term and remains a symbol of Chicano style and resistance.',
             'The museum had an exhibit on pachuco style and music.'),
 'caló': ('It was historically used by pachucos and is still studied by linguists.',
          'It is an in-group speech style, and phrases from it identify a speaker as part of a specific community.',
          "Some of his grandfather's phrases were pure caló from the old neighborhood."),
 'sale': ('This Mexican slang form comes from the verb salir, meaning to go out, and is used as a quick agreement.',
          'It is a short, casual reply among friends.',
          "Sale, I'll meet you there at six."),
 'homeboy': ('It is widely used in Chicano and Black communities in Los Angeles, and the shortened form homie spread nationally.',
             'The word shows how Chicano and Black speech in Southern California shaped each other.',
             'He ran into a homeboy from his old block at the airport.'),
 'lonche': ('This Spanglish loanword reshapes the English spelling to Spanish sound patterns.',
            'It appears on menus and in business names in Latino neighborhoods.',
            'We ate lonche at the diner.'),
 'troca': ('It is a Spanglish word used in many Mexican American communities.',
           'The spelling follows Spanish pronunciation, which is why it is easily spotted in writing.',
           'He parked his troca in front of the house.'),
 'parquear': ('This Spanglish verb combines English park with Spanish verb endings.',
              'It is common in the United States and Puerto Rico, although some Spanish speakers prefer aparcar or estacionar.',
              'Where did you parquear the car?'),
 'yarda': ('It is a Spanglish word for a lawn or a garden.',
           'It is the kind of borrowing that purists criticize and everyday speakers use constantly.',
           'The kids are playing in the yarda.'),
 'aseguranza': ('This Spanglish word replaces the standard Spanish seguro with a form shaped by English.',
                'Purists dislike it, but many speakers use it for car and health plans.',
                'We need to renew the aseguranza for the car.'),
 'textear': ('It is a Spanglish verb formed by adding Spanish verb endings to the English word.',
             'It appears in bilingual teenage speech and social media.',
             'Textéame when you get there.'),
 'rentar': ('This widely used Spanglish verb replaces alquilar in many American Spanish-speaking households.',
            'It is so common that some speakers do not realize it is a borrowing.',
            'Ellos rentan un apartamento cerca del trabajo.'),
 'janguear': ('It is a Puerto Rican Spanglish verb built from the English hang out.',
              'The form shows how English verbs enter Spanish through familiar endings.',
              'Vamos a janguear en la playa.'),
 'marqueta': ('This Puerto Rican and New York Spanglish word is used in the name La Marqueta in East Harlem.',
              'It is a place name as well as a common noun.',
              'We bought fruit at La Marqueta.'),
 'boricua': ('It is a self-identifying word used with pride on the island and in the diaspora.',
             'It is warm among Puerto Ricans and used less casually by outsiders.',
             'She wore a Boricua flag to the parade.'),
 'nuyorican': ('The word is associated with the Nuyorican Poets Café, founded in 1973.',
               'It identifies both heritage and place.',
               'The poet is a Nuyorican who writes in English and Spanish.'),
 'wepa': ('It is a Puerto Rican expression often shouted during celebrations.',
          "It is closely tied to the island's music and parades.",
          'Wepa, the music just started!'),
 "pa'lante": ('It was a Puerto Rican slogan used by the Young Lords in the 1960s and 1970s.',
              'It carries political and cultural weight beyond its literal meaning.',
              "He ended the speech with pa'lante."),
 'bochinche': ('The word is used in Puerto Rico and across the Caribbean.',
               'It can describe a loud argument as well as idle talk.',
               'There was a lot of bochinche about the wedding.'),
 'bregar': ('This Puerto Rican verb often covers dealing with problems or people.',
            'It is an everyday word that can sound blunt to speakers from other regions.',
            'I have to bregar with the paperwork tomorrow.'),
 'chévere': ('The term is common across the Caribbean, Colombia, and Venezuela, and its exact origin is debated.',
             'Speakers from Mexico may recognize it as a Caribbean or South American marker, which makes it a good sign of regional background.',
             'The concert was chévere from start to finish.'),
 'pana': ('The word is used in Venezuela, Ecuador, Puerto Rico, and parts of Colombia as a casual way of saying friend.',
          'It is especially common among young men and can attach to a name as a friendly address.',
          "Pana, I'll see you tomorrow."),
 'vaina': ('It is used in Dominican, Venezuelan, and Colombian Spanish.',
           'It can mean an object, an issue, or a problem depending on tone.',
           'What is that vaina on the table?'),
 'dime a ver': ('It is a Dominican phrase that literally means tell me to see.',
                'It marks a speaker as likely Dominican or in close contact with the community.',
                'Dime a ver, how is your day?'),
 'qué lo qué': ('This Dominican greeting is a stretched form of what is it, and it spread through merengue, bachata, and social media.',
                'It sounds playful and warm among friends, though it can be too casual for formal settings.',
                'Qué lo qué, my friend, long time no see.'),
 'tigueraje': ('This Dominican cultural idea celebrates cleverness and survival.',
               'It can be admired as resourcefulness or criticized as trickery.',
               'He has tigueraje and always finds a way.'),
 'guagua': ('It is used in Puerto Rico, Cuba, and the Dominican Republic as well as the Canary Islands.',
            'It shows how Caribbean Spanish differs from the Spanish of Spain and Mexico.',
            'We took the guagua to the city.'),
 'yuma': ('In Cuban slang the word names the United States, and it became widely known through songs and migration stories.',
          'Speakers use it with a hint of humor or longing, depending on whether they are discussing relatives abroad or a dream destination.',
          'His cousin lives in the yuma now.'),
 'asere': ('The word is widely used in Cuban Spanish and may have roots in Abakuá, the ritual language of an Afro-Cuban mutual aid society.',
           'It is mostly used among men, and it appears in songs and greetings as a friendly address.',
           "Asere, what's going on?"),
 'mano': ('The word is a clipped form of hermano and is common in Dominican and Puerto Rican speech.',
          'It works much like bro in English, and tone decides whether it sounds affectionate or insistent.',
          'Mano, did you hear the news?'),
 'jevo': ('They are used in the Caribbean and among diaspora speakers.',
          'The words are informal and used among peers.',
          'She introduced her jevo to the family.'),
 'cipote': ('The word is used in Salvadoran and Honduran Spanish for a child, and it often appears in affectionate phrases from family life.',
            'In some other countries the same word is vulgar, so travelers should be cautious with it.',
            'The cipote ran across the yard.'),
 'chivo': ('The word literally means goat, and in Salvadoran and Guatemalan speech it has become an adjective of praise.',
           'Friends use it for events, songs, and outfits that are impressive, and it identifies the speaker with Central America.',
           'The concert was so chivo.'),
 'vos': ('This feature, called voseo, replaces tú in many regions.', 'It is a marker of regional identity.', 'Vos sabés cómo llegar, ¿verdad?'),
 'pisto': ('It is a Guatemalan colloquialism that is not used in Mexico.',
           'It shows regional vocabulary differences.',
           "He doesn't have enough pisto for the bus."),
 'cabal': ('It is a Guatemalan affirmation that signals agreement.', 'It often stands alone as a quick reply.', "Cabal, that's what I meant."),
 'parce': ('It is strongly associated with the Antioquia region.', 'It spread through music and online media.', 'Parce, vamos a comer algo.'),
 'bacano': ('It is used across Colombia.', 'It is a positive word that works for people and events.', 'Qué bacano, that was an amazing trip.'),
 'che': ('It is a regional marker of Argentine speech.',
         'It is a casual address that is also an emblem of national identity.',
         'Che, did you see the match?'),
 'piola': ('The term comes from lunfardo, the street slang of Buenos Aires, and spread across Argentina and Uruguay.',
           'It describes people with clever style as well as things that look good, which makes it a flexible compliment.',
           'That jacket is piola.'),
 'laburo': ('It is from lunfardo and comes from Italian lavoro.',
            'It reflects the history of Italian immigration in Buenos Aires.',
            'I have a lot of laburo this week.'),
 'opo': ('They are built into Tagalog grammar as politeness markers that attach to sentences and answers.',
         'Leaving them out when speaking to an elder can seem rude even if the words are correct.',
         "Opo, I'll bring the food over right after school."),
 'kuya': ('This is a Filipino practice of extending family titles to non-relatives.',
          'The titles create closeness while keeping a clear sense of respect.',
          'Kuya, could you help me carry these bags?'),
 'tito': ('The titles extend kinship to older acquaintances in Filipino culture.',
          'The joking label titas of Manila has become a social media shorthand for a certain stylish older woman.',
          'Tita Marie always brings the best dessert to our parties.'),
 'pasalubong': ('The Filipino custom is rooted in the idea that travelers should share something from their journey.',
                'The gift is often an unspoken social expectation, especially when someone returns from abroad.',
                'He came home from the airport with pasalubong for everyone.'),
 'kilig': ('This Tagalog word is hard to translate and has no exact English equivalent.',
           'It is widely used in fandom and romance talk, especially for a scene that makes viewers squeal.',
           'I got kilig watching the proposal video.'),
 'gigil': ('This Tagalog emotion word has become popular among English speakers because it names a feeling that English lacks.',
           'The feeling is playful and affectionate, and it often appears with babies and pets.',
           'The puppy was so cute that I felt gigil.'),
 'hugot': ('The practice became popular in Filipino social media and film in the 2010s.',
           'Hugot lines became a genre of their own, with comedy shows and movies built around them.',
           'Her caption was a hugot about waiting for someone who never came.'),
 'sana all': ('This Filipino social media phrase spread in 2020 and then moved into international online talk.',
              'It expresses playful envy rather than real jealousy.',
              'He got a new bike, sana all!'),
 'charot': ('It comes from Filipino gay lingo, also called swardspeak, a creative argot built from wordplay.',
            'The word has spread from that community into general Filipino slang.',
            "I'm quitting my job, charot."),
 'chika': ('It is a word from Filipino gay lingo that moved into mainstream youth slang.',
           'It often appears in the phrase magchika, meaning to chat.',
           "Let's get coffee and share the chika."),
 'bes': ('It spread through Filipino social media and group chats.',
         'The form is affectionate and often used between women, though friends of any gender may use it.',
         'Bes, you have to try this place.'),
 'jowa': ('This Filipino slang word is widely used among young people and in swardspeak.',
          'It implies a more casual relationship than a formal partner.',
          'She introduced her jowa to the whole family.'),
 'gora': ('It comes from Filipino gay lingo, where the English word go is reshaped into a playful form.',
          'The word has become part of mainstream youth speech in the Philippines.',
          'Gora na, the train is leaving.'),
 'lodi': ('It is an example of Filipino backslang, a tradition of playing with syllables.',
          "The word usually appears online in comments praising someone's skill.",
          'Lodi, your work is amazing.'),
 'petmalu': ('The word was popularized online in 2016 and then entered Filipino pop culture.',
             'It usually praises impressive skill or cleverness.',
             'That edit was petmalu.'),
 'tara': ('In Tagalog, this common word invites someone to come along.',
          'It is a friendly invitation among peers.',
          "Tara, let's grab something to eat."),
 'sige': ('This Tagalog word signals agreement and is also a polite way to end a conversation.',
          'The sense changes slightly with tone, so the same word can mean fine or goodbye.',
          "Sige, I'll call you later."),
 'nako': ('This Tagalog interjection is a shortened form of a longer expression.',
          'It often stands alone as a sigh.',
          'Nako, I forgot my keys again.'),
 'susmaryosep': ('It is a Filipino expression with Catholic roots.',
                 'It is mild but religious in origin, so some speakers avoid it.',
                 'Susmaryosep, look at the mess in here!'),
 'bahala na': ('This Filipino phrase is also described as a cultural attitude of facing uncertainty.',
               'It can express courage or resignation depending on the situation.',
               "I don't know what the exam will be like, bahala na."),
 'utang na loob': ('This Filipino cultural concept connects to family loyalty and reciprocity.',
                   'It explains why many people feel bound to repay kindness across years.',
                   'He supports his parents out of utang na loob.'),
 'taglish': ('It is a widely used code-mixing style in the Philippines and the Filipino diaspora.',
             'It is a normal part of urban speech and is used in media, advertising, and school.',
             "Let's meet na lang at the mall later."),
 'ewan': ('This Tagalog expression is a contraction of a longer phrase.', 'It can sound dismissive when said sharply.', 'Ewan, ask someone else.'),
 'dạ': ('It is a Vietnamese politeness marker that is common in southern Vietnamese speech.',
        'Its use shows respect, so omitting it with elders can feel abrupt.',
        'Dạ, I understand.'),
 'anh chị em': ('The Vietnamese system lets speakers choose pronouns according to relative age and relationship.',
                'The choice signals closeness and respect, so picking the wrong one can be awkward.',
                'Chị, could you help me with this form?'),
 'ăn cơm chưa': ("This Vietnamese conversational greeting expresses concern for someone's wellbeing.",
                 'It parallels greetings in other Asian languages that ask about meals.',
                 'She asked ăn cơm chưa as soon as I arrived.'),
 'việt kiều': ('It is a Vietnamese term for the diaspora and appears in travel and family talk.',
               'It can be neutral or imply a sense of distance, especially around money and returning visitors.',
               'He is Việt Kiều and visits Vietnam each summer.'),
 'trời ơi': ('This Vietnamese exclamation is common among all ages.',
             'It can express dismay, surprise, or frustration.',
             'Trời ơi, that was so close!'),
 'sanuk': ('It is a Thai cultural concept that shapes how people approach work and play.',
           'It explains why Thai workplaces often blend fun with productivity.',
           'He believes that even chores should have a bit of sanuk.'),
 'mai pen rai': ('This Thai phrase of reassurance reflects a calm attitude toward setbacks.',
                 'It is one of the most recognized phrases among visitors to Thailand.',
                 'I spilled the water, but she said mai pen rai.'),
 'kreng jai': ('This Thai concept of consideration is difficult to translate directly.',
               'It can lead to polite refusals even when someone would welcome help.',
               "He felt kreng jai and didn't ask for help."),
 'jai yen': ('It is a Thai phrase that advises composure.', 'It is often said to someone who is upset.', 'Jai yen, we still have time.'),
 'nyob zoo': ('The Hmong greeting is used throughout the day and has become a common phrase at Hmong American community events.',
              'It is polite enough for elders and friendly enough for peers, and Hmong youth often use it online to show pride.',
              'Nyob zoo, how are you today?'),
 'ua tsaug': ('This is a standard Hmong expression of gratitude.',
              'It is widely used in Hmong American communities.',
              'Ua tsaug for helping us with the move.'),
 'aegyo': ('It is a Korean term that became popular worldwide through K-pop and K-drama.',
           'It is a performance of cuteness and can be playful or strategic.',
           'She did aegyo to convince her friend to share dessert.'),
 'daebak': ('This Korean exclamation became widely known internationally through K-pop fandoms.',
            'It is common in fan communities and can describe a performance or an event.',
            'The final scene was daebak.'),
 'hwaiting': ('It is a Korean expression derived from the English word fighting.',
              'It is used for support before an exam or a competition.',
              'Hwaiting, you can do it!'),
 'oppa': ('They are Korean kinship terms used for close friends and romantic partners.',
          "The choice depends on the speaker's gender and the relationship, which makes the system hard for learners.",
          'She called her older friend unnie with a smile.'),
 'sunbae': ('These Korean terms describe hierarchy by seniority.',
            'They structure respect and responsibility within groups.',
            'He asked his sunbae for advice about the internship.'),
 'jjang': ('It is a Korean slang word used for impressive things.',
           'It is often written in all caps online for emphasis.',
           'That concert was jjang.'),
 'heol': ('This Korean slang word emerged in internet culture.', 'It expresses surprise or disbelief.', 'Heol, the tickets sold out.'),
 'kkondae': ('This Korean slang word describes a person who assumes authority because of age.',
             'It is a criticism often used for rigid bosses and relatives.',
             'His boss was a kkondae who never listened.'),
 'ajumma': ('These Korean terms can be neutral or slightly dismissive depending on tone.',
            'Context matters, since they can also be warm terms for neighbors and shopkeepers.',
            'The ajumma at the market gave me extra fruit.'),
 'mukbang': ('This Korean internet trend began around 2009 on streaming platforms.',
             'It spread worldwide and sparked debates about eating habits and loneliness.',
             'She watches a mukbang while she eats lunch.'),
 'nunchi': ("This Korean concept was popularized in English by Euny Hong's 2019 book.",
            'It is considered an important social skill in many Korean settings.',
            'He has strong nunchi and can tell when people are tired.'),
 'pali pali': ('This Korean expression is associated with the fast pace of modern Korean life.',
               "It is often cited in discussions of why Korea's technology and services move quickly.",
               'Pali pali, the train is leaving!'),
 'aigoo': ('This Korean interjection is used by speakers of every age.',
           'It can express exhaustion, pity, or fondness depending on tone.',
           'Aigoo, you must be exhausted.'),
 'hallyu': ('The term was coined in the late 1990s to describe the rapid spread of Korean music and television.',
            'It now covers music, drama, film, and beauty products.',
            'Hallyu has made Korean pop culture a global phenomenon.'),
 'kawaii': ('This Japanese word spread worldwide through anime, fashion, and character goods.',
            'It names an entire aesthetic and not just an adjective.',
            'The shop sells kawaii stationery with tiny animals.'),
 'sugoi': ('It is a Japanese exclamation that spread through anime fandoms.',
           'It can express awe at skill or surprise at size.',
           'Sugoi, that animation is incredible!'),
 'yabai': ('This Japanese slang word has flexible meaning that depends on tone.',
           'Young speakers use it for everything from a great meal to an emergency.',
           'Yabai, the line is huge.'),
 'oshi': ('It is a Japanese fandom word that became widely used with the idol and anime industries.',
          'It describes devotion and sometimes the act of promoting someone.',
          'She cheers for her oshi at every show.'),
 'otaku': ('This Japanese word once had a negative meaning but has become more accepted in fandom.',
           'It is both a label and an identity.',
           'He proudly calls himself an otaku.'),
 'senpai': ('These Japanese terms describe hierarchy by seniority.',
            'They became popular outside Japan through anime school stories.',
            'The kohai bowed to the senpai after practice.'),
 'ganbatte': ('This Japanese phrase offers encouragement before a challenge.', 'It is supportive and friendly.', 'Ganbatte on your exam!'),
 'itadakimasu': ('It is a Japanese custom that thanks everyone involved in the meal.',
                 'It is a polite habit practiced in homes and schools.',
                 'We said itadakimasu before the meal.'),
 'kakkoii': ('This Japanese adjective is used for people and objects.',
             'It is a counterpart to kawaii when something is cool rather than cute.',
             'His jacket is so kakkoii.'),
 'moe': ('This Japanese fan term emerged from otaku culture in the 1990s.',
         'It is specific to fandom and sometimes criticized for its focus on fictional characters.',
         'The character evokes moe in many fans.'),
 'waifu': ('These fan words come from Japanese English and spread on English-language anime forums.',
           'The use is playful, although some people mean it sincerely.',
           'He says that character is his waifu.'),
 'weeb': ('This internet word dates from the 2000s and is related to weeaboo.',
          'It can be a mild insult or a self-label.',
          'He is a weeb who owns every figurine.'),
 'isekai': ('This Japanese genre label has become a major category in anime and light novels.',
            'It is a recognizable trope with its own conventions.',
            'The new anime is an isekai about a student in a fantasy realm.'),
 'tsundere': ('It is a Japanese character type name used by fans around the world.',
              'The trope is common in romance anime.',
              'The heroine is a classic tsundere.'),
 'ikigai': ('This Japanese concept became a popular self-help term in English.',
            'It often appears in discussions of purpose and longevity.',
            'He said that teaching is his ikigai.'),
 'yyds': ('This Chinese internet abbreviation spread around 2020.', 'It is used for legendary people or things.', 'That player is yyds.'),
 'involution': ('The Chinese term went viral in 2020 when a photograph of a student reading while cycling circulated.',
                'It describes social pressure in school and work.',
                'The office culture felt like involution with endless overtime.'),
 'lying flat': ('It became a Chinese social movement phrase in 2021.',
                'It reflects frustration among young people with the demands of work.',
                'He chose lying flat over an exhausting career.'),
 'let it rot': ('This Chinese internet phrase appeared in 2022.',
                'It signals deep fatigue with social expectations.',
                'She said bai lan and stopped worrying about promotions.'),
 '996': ('The term comes from the Chinese tech industry and became known through an online protest in 2019.',
         'It has become a symbol of overwork.',
         'The startup was known for 996 hours.'),
 'laowai': ('This Mandarin word can be neutral or mildly condescending.',
            'Context matters, and some foreigners find it exclusionary.',
            'The shop owner called him laowai with a smile.'),
 'aiya': ('The exclamation appears in both Cantonese and Mandarin and expresses a range of feelings from mild annoyance to shock.',
          'It is often stretched out for emphasis, and stereotypes in film have made some Chinese Americans wary of outsiders imitating it.',
          'Aiya, I forgot my umbrella.'),
 'ayi': ('The word literally means aunt, specifically a maternal aunt, and speakers extend it to friendly older women.',
         'In some contexts it also names a domestic helper, so the meaning depends on the setting.',
         'Ayi gave us some tea.'),
 'abc': ('This term is used within the diaspora to describe a cultural position between two worlds.',
         'It can be neutral or humorous.',
         "He's an ABC who speaks limited Mandarin."),
 'fob': ('The term is used in-group and sometimes in an insulting way.',
         'It is potentially offensive from outsiders, although some Asian Americans use it playfully among friends.',
         'He described his own accent as FOB and laughed.'),
 'hongbao': ('This Chinese custom marks Lunar New Year and weddings.',
             'The red color symbolizes luck.',
             'She received a hongbao from her grandmother.'),
 'guanxi': ('This Chinese concept shapes trust in business and family networks.',
            'It is hard to translate and is not simply networking.',
            'He used his guanxi to find the job.'),
 'mianzi': ('This Chinese cultural concept shapes etiquette and conflict avoidance.',
            'People often act to protect their own face and the face of others.',
            'He wanted to save mianzi in front of the guests.'),
 'ganbei': ('This Chinese toast is used at banquets and celebrations.',
            'It encourages guests to drink together.',
            'Everyone shouted ganbei and raised their glasses.'),
 'chi fan le ma': ('This Mandarin phrase expresses concern and works as a greeting.',
                   'It is similar to the Vietnamese greeting about rice.',
                   'Her grandmother always asks chi fan le ma first.'),
 'm goi': ('This Cantonese expression is used for small favors and polite requests.',
           'It is different from do jeh, which is used for gifts.',
           'M goi, can I get through?'),
 'lai see': ('The Cantonese custom marks Lunar New Year and weddings.',
             'It follows rules about who gives and who receives.',
             'The kids lined up for lai see.'),
 'yum cha': ('This Cantonese tradition is a social meal that often happens on weekends.',
             'The phrase is used across the diaspora.',
             'We went for yum cha on Sunday morning.'),
 'yaar': ('This word is used across Hindi, Urdu, and Punjabi and in Indian English.',
          'It is warm and casual, and it often softens a request or complaint.',
          "Yaar, don't worry about it."),
 'arre': ('The Hindi interjection is used to call attention or to express surprise, and it has been a staple of Hindi cinema for decades.',
          'Tone can make it gentle or sharp, and it is easily recognized by desi viewers in comedy skits.',
          'Arre, wait for me!'),
 'desi': ('It is a self-identifying word in the diaspora that covers many nationalities.',
          'It is widely used but some find it too broad.',
          'The desi student association hosted a festival.'),
 'aunty': ('This South Asian custom extends family titles to community elders.',
           'It is warm, and in the diaspora it has become a source of humor and affection.',
           'Aunty gave us tea and snacks.'),
 'jugaad': ('This Hindi and Punjabi word celebrates ingenuity in the face of limited resources.',
            'It is often praised in discussions of innovation.',
            'They fixed the fan with a bit of jugaad.'),
 'timepass': ('It is an Indian English term that is common in everyday speech.', 'It has a lighthearted tone.', 'Watching reruns is my timepass.'),
 'prepone': ('This Indian English word is the opposite of postpone.',
             'It is accepted in South Asian English even if some dictionaries label it nonstandard.',
             "Let's prepone the meeting to tomorrow."),
 'bhai': ('This word is used in Hindi, Urdu, and other languages.', 'It is used for friends as well as relatives.', 'Bhai, come over.'),
 'didi': ('The Hindi and Bengali word for older sister has been extended to older women in neighborhoods and workplaces.',
          'Using it shows respect while keeping a warm, family-like tone.',
          'Didi helped me with homework.'),
 'bindaas': ('The Mumbai slang word comes from Marathi and became popular through Hindi films.',
             'It describes a free-spirited attitude that is relaxed rather than reckless.',
             'She is bindaas and never worries.'),
 'paisa vasool': ('This Hindi phrase is used to praise good value.', 'It is often applied to movies and meals.', 'The film was paisa vasool.'),
 'mast': ('The Hindi and Urdu word can mean intoxicated or carefree, and in casual slang it means excellent.',
          'Friends use it for food, songs, and plans that feel just right.',
          'The food was mast.'),
 'kya baat hai': ('This Hindi phrase can express surprise or praise.',
                  'It is used for achievements and skills.',
                  'Kya baat hai, that was beautiful.'),
 'bakwaas': ('This Hindi word is used to dismiss claims or ideas.', 'It is common in family arguments.', "That's total bakwaas."),
 'hinglish': ('It is a widely used code-mixed style in speech, advertising, and film.',
              'It is common in media and online communities.',
              "Let's do a quick chai break yaar."),
 'abcd': ('This humorous term from the diaspora describes people between two cultures.',
          'Some find it offensive, and others use it affectionately.',
          'He called himself an ABCD with a laugh.'),
 'da kine': ('This core Pidgin word can replace almost any noun or verb.',
             'Its meaning depends on context, which is part of its charm.',
             'Pass me da kine over there.'),
 'brah': ("These words are used in Hawai'i Creole as friendly forms of address.",
          'They are warm and widely recognized.',
          'Brah, you coming to the beach?'),
 'shoots': ("The Hawai'i Creole word is a short agreement that has been used by local speakers for generations.",
            'It can mean okay, sure, or goodbye depending on how it is said.',
            'Shoots, see you at six.'),
 'pau': ("The word comes from Hawaiian and is widely used in Hawai'i.", 'It is used for tasks and for meals.', "I'm pau with work for the day."),
 'ono': ('The word comes from Hawaiian and is used in local food talk.', 'It also names a fish.', 'That plate lunch was ono.'),
 'grindz': ("The word is Hawai'i Creole slang for food, probably from the verb grind, meaning to eat.",
            'It appears in the names of local plate lunch spots and conveys a casual, filling meal.',
            "Let's go get some grindz."),
 'choke': ("The word means a lot in Hawai'i Creole, and its origin is uncertain.",
           'Newcomers may be startled to hear it in a happy sentence, since the English verb choke has a very different meaning.',
           'We had choke fun at the party.'),
 'talk story': ("This Hawai'i Creole phrase describes a relaxed conversation.",
                'It reflects a slow social rhythm.',
                'We sat on the porch to talk story.'),
 'akamai': ('The word comes from Hawaiian and is used in everyday speech.',
            'It can describe both intelligence and good judgment.',
            'She is so akamai with computers.'),
 'lolo': ('The word comes from Hawaiian.', 'It is used playfully in Pidgin.', "You're lolo if you think that will work."),
 'kapu': ('This Hawaiian word refers to sacred prohibitions and now appears on signs.',
          'It carries cultural weight and should be respected.',
          "The area is kapu, so don't enter."),
 'pau hana': ('The phrase comes from Hawaiian and names both the time and the social gathering.',
              'It is a common phrase in local bars.',
              'We meet at pau hana for drinks.'),
 'howzit': ("The greeting is widely used in Hawai'i, where it blends English how is it with local pronunciation, and it is also common in South "
            'Africa.',
            'In both places it works as a friendly hello that often replaces a longer greeting.',
            'Howzit, brah?'),
 'shaka': ("The hand gesture is associated with Hawai'i, with several stories about its origin, including a local man named Hamana Kalili.",
           'It conveys friendliness, gratitude, or relaxation, and it is often used while driving as a thank you.',
           'He gave me a shaka from the car.'),
 'ohana': ('The word comes from Hawaiian and includes extended family and close friends.',
           "It is widely quoted outside Hawai'i.",
           'Ohana means nobody gets left behind.'),
 'pupu': ('The word comes from Hawaiian and is used in restaurants.', 'It describes small shared dishes.', 'We shared some pupu before dinner.'),
 'hana hou': ('The phrase comes from Hawaiian and is used at concerts.', 'It is a request for an encore.', 'The crowd shouted hana hou.'),
 'slippahs': ("This Hawai'i word for sandals reflects Pidgin pronunciation.", 'It is a local term.', 'I left my slippahs at the door.'),
 'kolohe': ('The Hawaiian word means rascal or mischievous and is used in Pidgin for playful troublemakers.',
            'People say it with a smile about children and sometimes about adults who like pranks.',
            'That kolohe boy hid my keys.'),
 "mo' bettah": ('The phrase is Pidgin for more better and is widely recognized from local slogans and product names.',
                "It carries the island's casual humor and is often used in commercials and storefronts.",
                "This place is mo' bettah than the last one."),
 'no can': ("The Pidgin phrase follows a regular rule of making negatives with no, and it is a well-known example of how Hawai'i Creole grammar "
            'differs from standard English.',
            'It can mean cannot, not possible, or not allowed, depending on context.',
            "No can, I'm busy tonight."),
 'bumbye': ('The Pidgin word comes from the English phrase by and by and is found in several Pacific creoles.',
            'It can mean later or otherwise, as in do it or bumbye you get in trouble.',
            'Bumbye we go.'),
 'pc bang': ('The institution developed in the late 1990s.',
             'It was central to esports culture.',
             'He spent his weekends at the PC bang playing StarCraft.'),
 'gosu': ('The Korean word means master or expert, and it entered English-language gaming through StarCraft and other Korean-dominated esports.',
          'Calling someone a gosu is an honor, and it often appears in streams as praise for a skillful play.',
          'That player is a gosu.'),
 'wibu': ('The word entered Vietnamese and Indonesian online speech from English weeaboo and became a self-label for anime fans.',
          'Depending on the speaker it can be teasing, critical, or proudly self-descriptive.',
          'He is a wibu with a shelf of posters.'),
 'wah gwaan': ('The phrase is Jamaican Patois for what is going on, and it spread worldwide through reggae and dancehall.',
               'The spelling wagwan reflects how listeners hear it rather than a fixed standard.',
               'Wah gwaan, my friend, long time no see.'),
 'irie': ('It is a Jamaican word closely associated with Rastafari culture and widely heard in reggae lyrics.',
          'The word signals a relaxed, positive mood rather than a specific object.',
          'The beach was irie and the music was perfect.'),
 'yaad': ('In Jamaican speech the word refers to home or to Jamaica itself.',
          'The phrase back a yaad is used by people in the diaspora when they return to the island.',
          'She grew up in New York but spends every summer back a yaad.'),
 'likkle': ('This Jamaican Patois spelling reflects the creole pronunciation of little.',
            'It appears widely in captions and song titles, where the spelling signals a Caribbean voice.',
            "Give me a likkle time and I'll be there."),
 'nuff': ('The Jamaican word is a clipped form of enough and is used for large quantities.',
          'It appears in the phrase nuff respect, which became a common way to praise someone.',
          'There was nuff food at the party.'),
 'pickney': ('This Jamaican word may derive from Portuguese or English roots, and linguists discuss both possibilities.',
             'It is a normal word in Jamaican families, though it can sound babyish to outsiders.',
             'The pickney are playing in the yard.'),
 'bredda': ('This Jamaican Patois form of brother reflects the creole pronunciation.',
            'It appears often in reggae and dancehall lyrics as a friendly address.',
            'Bredda, can you give me a ride?'),
 'dutty': ('The word appears in reggae and dancehall with both literal and admiring meanings.',
           'Context decides whether the speaker means a mess or a hard-hitting beat.',
           'The dutty beat made the crowd move.'),
 'mash up': ('This Jamaican Patois phrase has a double sense that is common in dancehall.',
             'It can describe a ruined car or a performance that took over the stage.',
             'The band mashed up the stage with a huge performance.'),
 'bashment': ('The Jamaican word can describe a dance party, a style of music, or the whole scene.',
              'It also names a British Caribbean music style associated with London and Birmingham.',
              'The weekend bashment lasted until dawn.'),
 'big up': ('This Jamaican Patois phrase entered hip-hop and British slang through radio and dancehall.',
            'It appears in shout-outs on mixes and in greetings.',
            'Big up to everybody who came out tonight.'),
 'bless up': ('It is a Jamaican and Rastafari expression with a spiritual tone.',
              'The phrase is sincere when used in the community and sounds like imitation when used as a catchphrase.',
              "Bless up, I'll see you tomorrow."),
 'nyam': ('The Jamaican verb has African language roots, and similar words exist in several West African languages.',
          'It is used in food talk and lyrics, often with relish.',
          'Come nyam some rice and peas with us.'),
 'duppy': ('This Jamaican word is related to West African beliefs about spirits.',
           'It appears in stories, songs, and humorous warnings.',
           'The old house is said to be full of duppies.'),
 'tun up': ('This Jamaican Patois form shows how creole pronunciation reshapes English words.',
            'It appears in dancehall and is widely understood by fans.',
            'The DJ told us to tun up.'),
 'link up': ('It is used in Jamaican, British Black, and many other communities.',
             'The phrase shows how Caribbean speech influenced everyday English in cities such as London.',
             "Let's link up at the park later."),
 'soon come': ('This Jamaican phrase jokes about island time and flexible schedules.',
               'It is a cultural shorthand for arriving when the moment is right.',
               'He said soon come, which meant an hour at least.'),
 'cyaan': ('The Jamaican Patois spelling reflects the creole pronunciation of cannot.',
           'It appears frequently in lyrics and captions.',
           'Mi cyaan believe it.'),
 'unu': ('This Jamaican word likely comes from West African languages and fills a gap that standard English leaves.',
         'It is used across the island in everyday speech.',
         'Unu come help me with this.'),
 'rude boy': ('The Jamaican term emerged in the 1960s and entered British youth culture through the music.',
              'It later shaped fashion subcultures such as ska and two-tone.',
              'The rude boy look included a sharp suit and hat.'),
 'lime': ('This word is widely used in Trinidad and across the eastern Caribbean.',
          'It is different from the American fruit and the British verb for being late, a difference that confuses newcomers.',
          'We went to lime at the beach after work.'),
 'fete': ('The Trinidadian word comes from the French fête.', 'It is closely associated with Carnival season.', 'The weekend fete was packed.'),
 'wine': ('This Caribbean dance word appears in soca and dancehall.',
          'It is a social dance practice and not a casual gesture, so context matters.',
          'She learned to wine at her first carnival.'),
 'doh': ('This Trinidadian pronunciation appears in speech and writing.',
         'The spelling reflects the sound of the word in Trinidadian English Creole.',
         'Doh worry about it.'),
 'ent': ('This Trinidadian tag appears at the end of sentences.',
         'It is similar to British innit but has a different origin.',
         "It's hot today, ent?"),
 'bacchanal': ('The Trinidadian use stretches an old English word for a drunken festival.',
               'It appears in Carnival songs and in jokes about gossip.',
               'There was bacchanal at the fete last night.'),
 'mamaguy': ('This Trinidadian word suggests flattering someone to get your way.',
             'It is lighthearted and often used with a smile.',
             'Stop mamaguying me and tell me the truth.'),
 'steups': ('This Caribbean practice has West African roots and is written in several ways.',
            'It is a nonverbal expression that can be sharp or mild.',
            'She let out a long steups when he said that.'),
 'tabanca': ('This Trinidadian word appears in soca songs.', 'It is a dramatic word for a dramatic feeling.', 'He has tabanca since she left.'),
 'jumbie': ('This Caribbean word is related to West African and Creole folklore.',
            'Children grow up hearing jumbie stories at night.',
            'The children told jumbie stories at night.'),
 'wuh loss': ('This Barbadian phrase literally asks what loss.', 'It is similar to oh no or what a shame.', 'Wuh loss, I forgot my keys.'),
 'whappen': ('The greeting is a short form of what is happening, used in Guyanese and other Caribbean speech.',
             'It usually invites a casual update, and the reply can be as simple as nothing much.',
             'Whappen, how are things?'),
 'sak pase': ('This standard greeting means what is happening.', 'The usual reply is nap boule.', 'Sak pase, my friend?'),
 'nap boule': ('This Haitian Creole phrase literally means we are boiling.',
               'It is the usual reply that signals things are fine.',
               'Nap boule, thank you.'),
 'kompa': ('It developed in the 1950s and is central to Haitian culture.',
           'The word names the music and the slow, close partner dance.',
           'The kompa band played all night.'),
 'abeg': ('The Nigerian Pidgin word comes from the English phrase I beg.',
          'It can also express exasperation, as in a demand to stop.',
          'Abeg, give me a moment.'),
 'wahala': ('This Nigerian Pidgin word is generally linked to Hausa and Yoruba.',
            'It appears in the phrase no wahala, meaning no problem.',
            'No wahala, we can fix it.'),
 'gist': ('This is an English word that took on a specialized meaning in Nigerian speech.',
          'To gist someone means to chat or share news.',
          'I have a gist for you about the wedding.'),
 'japa': ('The word comes from Yoruba and became a Nigerian social media term around 2021.',
          'It is associated with the wave of professionals leaving Nigeria for opportunities abroad.',
          'Many of my friends decided to japa this year.'),
 'sapa': ('This Nigerian slang word describes severe lack of money.',
          'It is humorous but also reflects real economic pressure.',
          "I can't go out because of sapa."),
 'oga': ('This Yoruba word is used in Nigerian Pidgin to address someone with authority.',
         'It can be respectful or playful depending on the speaker.',
         'Oga, can we have a table?'),
 'owambe': ('The Yoruba word refers to weddings and celebrations where guests dress in matching fabric.',
            'It describes the party and the style of dressing.',
            'We attended an owambe on the weekend.'),
 'chop': ('This West African Pidgin word also means to spend.', 'It appears in phrases such as chop money.', 'Come and chop some jollof rice.'),
 'vex': ('The word comes from English vex and is common in West African Pidgin.',
         'It is used where standard English would say angry.',
         'I vex for what he said.'),
 'sabi': ('This Pidgin word comes from Portuguese saber.', 'The same root appears in many creoles around the world.', 'I sabi the way.'),
 'wetin': ('This Nigerian Pidgin question word comes from what thing.', 'It appears in greetings such as wetin dey.', 'Wetin you dey do?'),
 'oya': ('This Yoruba word is used in Nigerian speech to urge action.', 'It works as a friendly nudge.', "Oya, we're going to be late."),
 'pikin': ('This Pidgin word comes from Portuguese pequeno.', 'It appears across West African and Caribbean creoles.', 'The pikin is sleeping.'),
 'gbedu': ('The Yoruba word names a type of drum and has become slang for strong bass.',
           'It appears in Nigerian music writing.',
           'The DJ dropped some gbedu.'),
 'charley': ('It comes from the name Charlie and became a general address in Ghanaian English.',
             'It is similar in feel to the Mexican chale but unrelated.',
             "Charley, let's go."),
 'yawa': ('This West African Pidgin word is used in Ghana and Nigeria.',
          'It often appears in the phrase yawa dey.',
          'There will be yawa if we miss the bus.'),
 'sasa': ('The word comes from Swahili sasa, meaning now.', 'It is a standard greeting in Nairobi.', 'Sasa, how are you?'),
 'poa': ('This Kenyan Sheng word comes from Swahili poa, meaning cool.', 'It is the usual reply to sasa.', 'Poa, thanks.'),
 'niaje': ('The Sheng greeting is a contraction of Swahili phrases meaning how are you, and it spread through Nairobi youth culture.',
           'It is used among peers and sounds too casual for formal introductions.',
           'Niaje, bro?'),
 'manze': ('The Sheng exclamation comes from the Swahili word for man and is similar in feel to English dude.',
           'It can express surprise, sympathy, or emphasis depending on the sentence.',
           'Manze, that was crazy.'),
 'lekker': ('This South African English word is used for food, weather, and events.',
            'It spread beyond Afrikaans speakers into general South African speech.',
            'The braai was lekker.'),
 'eish': ('This South African interjection is used across language groups.',
          'Its meaning shifts with tone from sympathy to dismay.',
          'Eish, that was close.'),
 'braai': ('This word comes from Afrikaans and names a social gathering as well as the cooking method.',
           'It is a cultural symbol with a national day of celebration.',
           'We had a braai on Sunday.'),
 'now now': ('This South African phrase is vaguer than just now.',
             'The difference between now now, just now, and now confuses visitors.',
             "I'll be there now now."),
 'amapiano': ('It developed in the 2010s in townships near Johannesburg and Pretoria.',
              'The genre has its own slang and dance styles.',
              'The club played amapiano all night.'),
 'ubuntu': ('This Nguni Bantu concept influenced South African political and ethical thought.',
            'It is quoted widely in leadership and community writing.',
            'The team lives by ubuntu.'),
 'wagwan': ('This form borrows from Jamaican Patois and is common among young Londoners.',
            'The spelling is a clear marker of London youth speech.',
            "Wagwan, how's your day?"),
 'peng': ('This MLE slang word is used for people, food, and outfits.',
          'Its origin is unclear, with some linking it to Caribbean usage.',
          'That dinner was peng.'),
 'bare': ('This MLE form works as an intensifier and quantifier and was described in sociolinguistic studies of London youth.',
          'Unlike standard very, it can attach to countable nouns.',
          'There were bare people at the event.'),
 'allow it': ('This MLE phrase tells someone to drop a topic or leave something alone.',
              'It was spread by grime and drill music.',
              "Allow it, we're not going."),
 'wasteman': ('The term comes from Jamaican waste man and is used in British youth speech.',
              'It is a clear insult and not a friendly teasing term.',
              "He's a wasteman who never helps."),
 'mandem': ('The word comes from the Jamaican phrase man dem, meaning the men.',
            'It is used in friendly contexts among young Londoners.',
            'The mandem are all coming.'),
 'roadman': ('The word draws on road as a name for street life in UK slang.',
             'The label can be descriptive or stereotypical, and some people reject it.',
             'He dressed like a roadman in a tracksuit.'),
 'ends': ('This UK slang word names the area where someone lives or grew up.',
          'It is similar to hood in American slang.',
          'I grew up in these ends.'),
 'peak': ('This UK slang word reacts to a bad turn of events.', 'It is a common reaction in conversation.', "That's peak, the bus just left."),
 'long': ('This MLE slang adjective describes tasks that feel exhausting.', 'It is typically used in complaints.', 'That walk is long.'),
 'bait': ('This slang use of bait describes something blatant or easily noticed.', "It appears in the phrase that's bait.", 'That lie was bait.'),
 'buzzin': ('This UK slang word is a version of buzzing.', 'It appears in casual speech and captions.', "I'm buzzin for the weekend."),
 'mugged off': ('This UK slang phrase describes being treated disrespectfully.',
                'It is used when someone feels humiliated.',
                'He felt mugged off by the cancellation.'),
 'skeen': ('This MLE form is a spoken version of I see.', 'It is a short response in conversation.', 'Skeen, thanks for explaining.'),
 'ting': ('The word comes from Jamaican Patois and is used widely in MLE.',
          'When used for a person it can be objectifying.',
          'That song is a mad ting.'),
 'blud': ('This MLE word is a shortened form of blood, meaning relative.', 'It is used among young men in London.', "Blud, that's wild."),
 'bruv': ('This British slang word is a short form of brother.',
          'Its widespread use across groups made it a stereotype in comedy.',
          'Bruv, pass the ball.'),
 'oh my days': ('This MLE phrase is widely used among Londoners.', 'It works like oh my goodness.', "Oh my days, I can't believe it."),
 'safe': ('This UK slang word is used to show agreement or gratitude.', 'Its precise origin is debated.', "Safe, I'll see you later."),
 'innit': ('This British tag question has been described in MLE research as an invariant tag that can follow any statement.',
           'It spread across many British communities.',
           "That's a good song, innit?"),
 'chuffed': ('The word comes from dialect chuff, meaning plump or pleased, and has been part of British slang for generations.',
             'It is often used for personal results such as exam grades or a new job.',
             "I'm chuffed with my results, and so is my whole family."),
 'knackered': ('The word is related to knacker, a person who bought worn-out horses to be slaughtered.',
               'It is more vivid than tired and is common in everyday British conversation.',
               "I'm knackered after a double shift at the restaurant."),
 'skint': ('The word is a variant of skinned, as in being stripped of everything.',
           'It is usually said with a tone of weary humor rather than real distress.',
           "I'm skint until the end of the month, so no restaurants for me."),
 'gutted': ('The word evokes the image of being emptied of feeling, and it became common in British sports talk and daily conversation.',
            'It can describe anything from a canceled holiday to a lost match.',
            'We were gutted when the final goal was disallowed.'),
 'mint': ('In much of northern England the word is used as a high compliment, with its meaning drawn from something freshly made.',
          "It appears in phrases such as that's mint.",
          'That new bakery is mint, and the pies are huge.'),
 'banter': ('The word has been used since the seventeenth century but gained a new life in British lad culture of the 2010s.',
            'People sometimes defend cruel jokes as banter, which makes the word contested.',
            'The group chat is full of banter about the football results.'),
 'cuppa': ('The word is a contraction of cup of and reflects the central role of tea in British social life.',
           'An invitation to a cuppa often means an invitation to talk.',
           'Come in for a cuppa and tell me everything.'),
 'naff': ('The word appeared in British slang in the 1960s, and some linguists link it to Polari.',
          'Its origin is uncertain, which makes it a good example of slang whose past is still debated.',
          'That novelty tie is completely naff.'),
 'polari': ('The vocabulary mixed Romani, Italian, backslang, and rhyming slang, and it helped people communicate privately when homosexuality was '
            'illegal.',
            'A few of its words entered general British slang, and scholars still debate which ones.',
            'The radio sketches of the 1960s made Polari familiar to a mass audience.'),
 'fit': ('In British youth slang, fit is the standard word for physically attractive, distinct from its meaning of healthy.',
         'Because it is so common in British comedy, American audiences may mistake it for a joke.',
         'Everyone agreed that the new teacher was fit.'),
 'proper': ('This intensifier is used across many British dialects and goes back to older meanings of correct or thorough.',
            'It adds friendly emphasis without being rude.',
            "It's proper cold this morning, so wear a coat."),
 'blimey': ('The word is a contraction of an old oath, God blind me, softened over time.',
            'It now sounds slightly theatrical, often used for comic effect.',
            'Blimey, look at the size of that queue.'),
 'bloke': ('The word is thought to come from Romani or Shelta and entered British and Australian slang in the nineteenth century.',
           'It describes an ordinary man in friendly terms and carries a sense of relaxed everyday masculinity.',
           "He's a decent bloke who always helps the neighbors."),
 'kip': ('The word is British and Irish slang with possible Danish roots meaning hut.',
         'It is informal and often used with have, as in have a kip.',
         "I'm going to grab a quick kip before the match."),
 'cheeky': ('In British English the word describes someone who is cheerfully disrespectful.',
            'It can be an affectionate description of children, friends, and even food or drink.',
            'We had a cheeky pint after work.'),
 'mate': ('The word is used across British, Irish, and Australian English as a general address.',
          'Its tone changes with the voice, and a hard mate can be a warning.',
          'Cheers, mate, I appreciate the lift.'),
 'craic': ('It is a respelling of English crack that became standard in Irish writing in the late twentieth century.',
           "It appears in the greeting what's the craic, which asks what is happening.",
           'The craic was mighty at the pub after the match.'),
 'grand': ('In Irish English the word is a very common reply that expresses mild approval.',
           'It can sound enthusiastic or barely polite depending on tone.',
           'How are you? Grand, thanks, and yourself?'),
 'eejit': ('The word reflects the Irish pronunciation of idiot.',
           'It can be affectionate, and it appears frequently in family teasing.',
           "Don't be such an eejit, you left the keys in the car."),
 'banjaxed': ('This Irish English word is generally traced to the early twentieth century, and its origin is uncertain.',
              'It is used for machines, plans, and sometimes people.',
              'The printer is banjaxed and the deadline is today.'),
 'deadly': ('In Irish English the word is a strong compliment unrelated to danger.',
            'It is especially common in Dublin speech.',
            'That gig was deadly, and the band played three encores.'),
 'giving out': ('The phrase in Irish English describes scolding or grumbling.',
                'It has nothing to do with handing something over.',
                'He was giving out about the weather all morning.'),
 'yoke': ("The word works much like jawn in Philadelphia or da kine in Hawai'i.",
          'It is a good example of how different communities use a placeholder noun.',
          'Pass me that yoke on the shelf there.'),
 'culchie': ('The word is used by city people and by rural people themselves.',
             'It can be teasing or mildly derogatory depending on who says it.',
             "He moved to Dublin for work, but he's a culchie at heart."),
 'sláinte': ('The Irish word is used as a toast around the world.',
             'It is a rare Irish word that is widely used even by non-speakers.',
             "Sláinte, everybody, here's to a great year."),
 'wee': ('This Scottish word is also used in Northern Ireland and is one of the most recognized Scots terms.',
         'It appears in affectionate phrases such as a wee cup of tea.',
         'A wee bit of sugar, please.'),
 'braw': ('The word is Scots and is used for weather, clothes, and people.',
          'Its sound makes it a common choice in Scottish songs and poems.',
          "It's a braw day for a walk along the shore."),
 'bairn': ('The word comes from the Old English and Old Norse roots of barn and is used in Scotland and northern England.',
           'It appears in songs and lullabies and feels especially tender in Scots speech.',
           'The bairn is asleep, so keep your voice down.'),
 'dinnae': ('This Scots spelling captures the pronunciation of do not.',
            'It is often seen in dialect writing and song lyrics.',
            "Dinnae fash yourself, we'll be there on time."),
 'ken': ('In Scots the verb is a standard part of speech.', "It appears in the question d'ye ken.", "D'ye ken what I mean?"),
 'dreich': ('The word is Scots and describes the specific misery of a gloomy day.',
            'It has become a popular emblem of Scottish weather.',
            "It's a dreich Monday morning, so bring an umbrella."),
 'blether': ('The Scots word comes from an older term for babbling and is used in both Scotland and Northern Ireland.',
             'A good blether is a chat that wanders happily through many topics.',
             'We sat for hours having a good blether.'),
 'numpty': ('The word is Scottish slang, and its origin is unclear.',
            'It is a mild insult that is often used affectionately.',
            'He walked into the glass door like a total numpty.'),
 'cwtch': ('This Welsh word has no precise English equivalent and is used as both noun and verb.',
           'It is a cherished word in Welsh English and a common gift-shop slogan.',
           'Come here for a cwtch, you look cold.'),
 'lush': ('In Welsh and Bristol English the word is a strong compliment.',
          'It may confuse American speakers who know only its meaning of leafy or luxuriant.',
          'That cake was lush and I want the recipe.'),
 'hiraeth': ('The Welsh word is often described as hard to translate.',
             'People use it to describe homesickness mixed with grief and love.',
             'She felt hiraeth every time she heard the old hymn.'),
 'butty': ('The word comes from an older term for a fellow worker, especially in mining communities.',
           'It appears in the greeting alright butt.',
           "He's my butty from the old mining town."),
 'arvo': ('The word shows the Australian habit of shortening a word and adding the o ending.',
          'Similar forms include servo, bottle-o, and smoko.',
          'See you this arvo at the beach.'),
 'servo': ('The word follows the Australian pattern of clipping a word and adding o.',
           'It is used in everyday speech and on signs.',
           'I stopped at the servo for petrol and a pie.'),
 'heaps': ('The word is common in Australian and New Zealand English as an all-purpose quantifier.',
           'It can modify nouns, verbs, and adjectives.',
           'Thanks heaps, that was really kind.'),
 'sook': ('The word is Australian slang and is likely related to sooky, meaning sulky.',
          'It is used as mild teasing.',
          "Don't be such a sook, it's only a scratch."),
 'cozzie': ('The word is a clipped form of costume with the Australian ie ending.',
            'It is part of beach and pool vocabulary.',
            'Pack your cozzie for the beach.'),
 'thongs': ('The word surprises Americans because of its other meaning.',
            'The Australian usage is the standard everyday word for beach footwear.',
            'Put your thongs on before you go outside.'),
 'ute': ('The word is short for coupe utility, a vehicle introduced in Australia in the 1930s.',
         'It is a common sight on farms and building sites.',
         'He drove a ute to work every day.'),
 'bogan': ('The word has been used in Australia since at least the 1980s.',
           'It can be affectionate self-description or a class-based insult.',
           'The comedian joked about the bogan stereotype for ten minutes.'),
 'maccas': ('The Australian nickname follows the clipped form with the as ending.',
            'It is so widespread that the company itself has used it in advertising.',
            "Let's get maccas for lunch."),
 'fair dinkum': ('The phrase dates from the nineteenth century and may come from English dialect.',
                 'It is now partly a stereotype of Australian speech.',
                 'Is that fair dinkum, or are you pulling my leg?'),
 'yeah nah': ('This Australian phrase is an example of how speakers soften refusals.',
              'It can also mean yes, so the second word must be heard in context.',
              "Yeah nah, I'll pass on dessert."),
 'selfie': ('The Oxford English Dictionary traces the earliest known use to an Australian online forum in 2002.',
            "The word became a global term and was named Oxford's Word of the Year in 2013.",
            'She took a selfie in front of the harbor.'),
 'chur': ('This New Zealand English word is believed to come from cheers.',
          'It is common among young New Zealanders.',
          'Chur, bro, I appreciate it.'),
 'sweet as': ('The as pattern is typical of New Zealand English, as in hard as and good as.',
              'It works as a stand-alone reply.',
              'Is Friday okay? Sweet as.'),
 'jandals': ('The New Zealand word comes from Japanese sandals and was trademarked in the 1950s.',
             'It is the everyday term for beach sandals.',
             'Where are my jandals?'),
 'dairy': ('The word is the New Zealand term for a convenience store.', 'It is part of everyday talk.', 'Pop down to the dairy for milk.'),
 'yalla': ('The word comes from Arabic and is used across Arabic-speaking regions, as well as in Hebrew, Turkish, and other languages.',
           'It is a friendly push and is often shouted in group settings.',
           "Yalla, we're going to miss the start of the game."),
 'habibi': ('The terms come from Arabic and are used in families, among friends, and in songs.',
            'They can sound romantic or merely friendly depending on tone and relationship.',
            'Habibi, come sit with us for dinner.'),
 'wallah': ('The words are Arabic and have religious meaning, although many young speakers use them as casual emphasis.',
            'Some people find casual use disrespectful because the original meaning is an oath.',
            'Wallah, I left the house on time and the bus never came.'),
 'inshallah': ('The Arabic phrase is used by Muslims and also by many Arabic-speaking Christians.',
               'It expresses humility about the future, and in conversation it can also soften a commitment.',
               "We'll see you next weekend, inshallah."),
 'mashallah': ('The Arabic phrase is spoken when someone praises a child, a home, or an achievement.',
               'It is considered polite to add it when complimenting something.',
               'Mashallah, your garden looks wonderful this year.'),
 'khalas': ('This Arabic word is widely used in Levantine and Gulf Arabic.',
            'It can end an argument or announce that a task is complete.',
            "Khalas, I've heard enough, let's move on."),
 'yaani': ('The Arabic word is used constantly in conversation as a filler and connector.',
           'In written chat it is often spelled with numbers as ya3ni.',
           "Yaani, I'm not sure what he wanted from us."),
 'sahtein': ('This Levantine Arabic phrase literally means two healths.',
             'It is a social courtesy at meals.',
             'Sahtein, I hope you enjoyed the food.'),
 'tayeb': ('The Arabic word is common in Levantine and Egyptian speech as a way to agree.',
           'It often begins a sentence, like well then.',
           'Tayeb, we can leave right after lunch.'),
 'akhi': ('The Arabic words are used in religious communities as a respectful and affectionate form of address.',
          'They carry a sense of shared faith, so outsiders may use them with care.',
          'Akhi, thanks for helping with the food drive.'),
 'bismillah': ('The Arabic phrase is spoken by many Muslims before eating, starting a task, or beginning a journey.',
               'It is a religious expression, and casual jokes about it can offend.',
               'He said bismillah before he took the first bite.'),
 'haram': ('The words are Arabic and have religious meanings, and young speakers have borrowed them as general slang.',
           'People inside the community may find the joking use funny, while outsiders may sound mocking.',
           'That was so haram, you ate my leftovers without asking.'),
 'arabizi': ('It developed in the 1990s on early chat and mobile phone platforms, with 3 for the letter ayn and 7 for the letter ha.',
             'It is a clear example of how young people adapt writing systems to technology.',
             'She wrote 7abibi in the group chat to greet her cousin.'),
 'joon': ('This Persian word is used in families and among friends, as in Sara joon.',
          'It signals warmth and closeness.',
          'Come here, Sara joon, and sit by me.'),
 'azizam': ('The Persian word means my dear one and is used in families and in songs.',
            'It can be a romantic or a family endearment.',
            'Azizam, did you eat anything today?'),
 'taarof': ('The practice shapes etiquette around gifts, payment, and hospitality.',
            'Outsiders may misread polite refusals as real rejections.',
            'He insisted on taarof, so the host offered the tea three times.'),
 'jigar': ('Persian speakers use the word in phrases such as jigaram, meaning my dear.',
           'It is an endearment that sounds strange in translation.',
           'Jigaram, come here and let me hug you.'),
 'uso': ('The word is used among Samoans and by many other Pacific Islander youth as an address of respect.',
         'It extends family language to friendships.',
         'Uso, come sit with us at the game.'),
 'palagi': ('The Samoan word is used in everyday speech, and its original meaning is debated.',
            'It can be neutral or slightly critical depending on context.',
            'The palagi visitor asked about the meaning of the tattoo.'),
 "fa'a samoa": ('The phrase describes a whole set of values and obligations.',
                'It is a central identity marker for Samoans around the world.',
                "He explained that fa'a Samoa guides every family decision."),
 'fia': ('Samoan speakers use the prefix to tease someone who is putting on airs.',
         'It is a common form of playful social correction.',
         "Don't be so fia poto, you only read the first page."),
 'malo': ('The word has several uses depending on context and language.',
          'It appears in greetings such as malo e lelei in Tongan.',
          'Malo, thank you for your help.'),
 'alofa': ('The word is used for family love and for affection toward friends.',
           'It is a core value in Samoan culture.',
           'She wrote alofa on the card for her grandmother.'),
 'ofa': ('The Tongan word is central to family and community values.',
         'It is used in greetings and song lyrics.',
         'The church service was full of ofa and music.'),
 'kia ora': ('The phrase is used in New Zealand English and increasingly worldwide.',
             'It is among the most familiar Maori words to outsiders.',
             'Kia ora, welcome to the meeting.'),
 'whanau': ('The word is used widely in New Zealand English and includes extended family, close friends, and community.',
            'Its use in government and schools reflects a shared commitment to collective responsibility.',
            'The whanau gathered for the long weekend.'),
 'mana': ('The word appears in Maori and in many other Polynesian languages.',
          'It has also entered video game vocabulary, where it names magic power.',
          'The elder carried a great deal of mana in the community.'),
 'aroha': ('The word is a central Maori value and a common name.',
           'It is used widely in New Zealand English.',
           'She greeted everyone with aroha and a warm smile.'),
 'mahi': ('The Maori word is used in New Zealand English for job or effort.',
          'It appears in phrases such as good mahi.',
          'Great mahi on the project this week.'),
 'hui': ('The word is used for formal gatherings and for community meetings.',
         'It is widely understood in New Zealand.',
         'The hui lasted all afternoon.'),
 'skoden': ("The phrase is based on the pronunciation of let's go then and became popular on social media among Native youth.",
            'Its tone is playful, and it is a clear in-group marker.',
            'Skoden, the show starts in ten minutes.'),
 'ndn': ('The form is used online and in conversation among Native communities.',
         'Outsiders should be cautious, because the word has a complicated history.',
         'The shop sold shirts with the word NDN in bold letters.'),
 'rez': ('The shortened form is used affectionately by many Native people to describe home communities.',
         'It appears in phrases such as rez life.',
         'He grew up on the rez and drives back every holiday.'),
 'indian time': ('The phrase is used in Native communities as an in-group joke, and its meaning has been debated.',
                 'Outsiders using it risk repeating a stereotype.',
                 'The elders said the ceremony would start on Indian time.'),
 'frybread': ('It traces to the forced relocation and rations provided by the United States government in the nineteenth century.',
              'The food is a source of community pride and also a symbol of historical hardship.',
              'The stand sold frybread with honey at the powwow.'),
 'powwow': ('The word comes from an Algonquian language, and its meaning has been widely borrowed in English.',
            'The general English use meaning any meeting sometimes bothers Native people.',
            'They traveled hours to attend the powwow.'),
 "yá'át'ééh": ('The Navajo greeting is widely recognized in the Southwest.',
               'It is part of everyday greetings across the Navajo Nation.',
               "Yá'át'ééh, welcome to the trading post."),
 "ahéhee'": ('It is used in daily conversation and in ceremony.',
             'It is a respectful way to show gratitude.',
             "Ahéhee' for the ride, we really appreciate it."),
 'boozhoo': ('The greeting is used across Anishinaabe communities in the Great Lakes region.',
             'It is often used at the start of meetings.',
             "Boozhoo, I'm glad to see everyone here."),
 'miigwech': ('The Ojibwe word of thanks is used in conversation, ceremony, and public speeches across the Great Lakes region.',
              'Speakers often say it at the end of a talk to show respect for listeners.',
              'Miigwech for sharing the story with us.'),
 'tansi': ('The Cree greeting is used across Canada and the United States.', 'It is a short and friendly opener.', 'Tansi, how are you today?'),
 'schlep': ('This Yiddish word entered American English through immigrant communities in New York.',
            'It implies a tiresome journey as well as heavy luggage.',
            'I had to schlep across town with three heavy bags.'),
 'chutzpah': ('The word comes from Yiddish and Hebrew and has an admiring and critical side.',
              'It is often explained with the joke about a person who kills his parents and then asks for mercy as an orphan.',
              'It took real chutzpah to ask for a raise on the first day.'),
 'mensch': ('The word comes from Yiddish and means human being in German.',
            'It is one of the highest compliments in Yiddish-influenced speech.',
            'He helped everyone move, which makes him a real mensch.'),
 'kvetch': ('The Yiddish verb entered English as both verb and noun.',
            'It often describes habitual complaining that is more comic than serious.',
            'She likes to kvetch about the weather every morning.'),
 'nosh': ('The word came into English from Yiddish and became common in delis and homes.',
          'It suggests small bites rather than a full meal.',
          'We ordered a plate of pickles to nosh on.'),
 'oy vey': ('The Yiddish phrase literally means oh woe and became a stock phrase in American comedy.',
            'It is used with humor and is sometimes overused in caricature.',
            'Oy vey, the printer jammed again.'),
 'schmooze': ('The word comes from Yiddish and often describes social conversation with a purpose.',
              'It can be affectionate or slightly cynical.',
              'The senator spent the evening schmoozing with donors.'),
 'mazel tov': ('The Hebrew and Yiddish phrase is used at weddings, graduations, and other joyful events.',
               'It is used by non-Jewish people too.',
               'Mazel tov on the new apartment!'),
 'kvell': ('The Yiddish verb describes bursting with pride.',
           'It is a warm word often used by parents and grandparents.',
           'Her grandmother kvelled when she heard the graduation speech.'),
 'klutz': ('The word comes from Yiddish klots, meaning a block of wood.',
           'It is a mild and affectionate insult.',
           "I'm such a klutz, I tripped over my own shoelaces."),
 'tchotchke': ('The Yiddish word is used in American English for trinkets and souvenirs.',
               'It is usually mildly dismissive and sometimes affectionate.',
               'The shelf was full of tchotchkes from every trip.'),
 'glitch': ('Many sources trace the word to Yiddish glitsh, meaning slip.',
            'It became widespread through the American space program of the 1960s.',
            'A software glitch delayed the whole schedule.'),
 'spiel': ('The word comes from German and Yiddish for play.',
           "It often describes a salesperson's rehearsed pitch.",
           'He gave the same spiel to every customer who walked in.'),
 'bupkis': ('The Yiddish word is often said with disdain.', 'It appears in comic dialogue.', 'After all that work, we got bupkis.'),
 'mishegas': ('The Yiddish word is used for chaotic situations.',
              'It suggests a mix of exasperation and humor.',
              'The holiday travel mishegas started on Wednesday.'),
 'shtick': ('The word comes from Yiddish and became a theatrical term.',
            'It can be affectionate or slightly critical.',
            'His shtick is to answer every question with a joke.'),
 'bubbe': ('The words are used in many Jewish American families.',
           'They are tender names tied to family tradition.',
           'Bubbe baked the challah for the whole family.'),
 'paisan': ('The word comes from the Italian paesano and was used in Italian American neighborhoods.',
            'It can be affectionate or used as a stereotype in films.',
            'The butcher greeted him as paisan and wrapped extra sausage.'),
 'mangia': ('The word became part of American speech through family restaurants and movies.',
            'It is typically used with humor.',
            'Mangia, there is plenty of food on the table.'),
 'capisce': ('The Italian word is often used as a tag in movies about organized crime.',
             'It can sound like a caricature when used by outsiders.',
             'Keep the noise down after ten, capisce?'),
 'gravy': ('The word is used in parts of New Jersey, New York, and Pennsylvania where others say sauce.',
           'Its use is a good-natured regional and family debate.',
           'Sunday means gravy simmering on the stove all morning.'),
 'gabagool': ('The word reflects southern Italian dialect pronunciation as heard in New Jersey and New York Italian American speech.',
              'Television made it a famous marker, and it is often used as caricature.',
              'He ordered a sandwich with gabagool and provolone.'),
 "madonn'": ('The word is used in Italian American speech as a mild religious interjection.',
             'It can sound sacred to some listeners and casual to others.',
             "Madonn', look at the size of that line."),
 'lagniappe': ('The word comes from Louisiana Creole and is borrowed from Spanish and Quechua roots.',
               'It is a beloved Louisiana word, often seen on shop signs.',
               'The baker slipped in a free cookie as lagniappe.'),
 'cher': ('The word comes from French and is common in Cajun speech.',
          'It is used with friends, children, and customers.',
          'Come on in, cher, the food is almost ready.'),
 'fais do-do': ('The phrase comes from French baby talk meaning go to sleep, since parents would put children to bed during the dance.',
                'It names a social event as well as a custom.',
                'We went to the fais do-do on Saturday night.'),
 'laissez les bons temps rouler': ('The French phrase is a Louisiana motto, especially at Mardi Gras.',
                                   'It is widely used in New Orleans tourism.',
                                   'The parade began with a cheer of laissez les bons temps rouler.'),
 'making groceries': ('It is a translation of the French faire son marché and is considered a distinctive local expression.',
                      'It is a marker of New Orleans speech.',
                      "We're making groceries this afternoon before the storm."),
 'neutral ground': ('The term is used in New Orleans, where the wide boulevard medians were the neutral border between French and American sections.',
                    'It shows how history leaves traces in everyday words.',
                    'They parked on the neutral ground during the parade.'),
 'second line': ('The term refers to the dancers who follow the main parade.',
                 'It is both a cultural event and a style of dancing.',
                 'The second line wound through the neighborhood with umbrellas and horns.'),
 'yat': ('The dialect has features similar to Brooklyn speech and is associated with working-class white and Black New Orleanians.',
         "The greeting where y'at means how are you.",
         "He greeted us with where y'at and a big smile."),
 'who dat': ('The phrase has roots in minstrel-era and local traditions, and its history is debated.',
             "It is a core part of the city's football identity.",
             'The crowd shouted who dat before kickoff.'),
 'pass a good time': ('The Louisiana French phrase appears in Cajun English.',
                      'It describes festival and family life.',
                      'We passed a good time at the crawfish boil.'),
 'bayou': ('The word comes from a Choctaw word and entered English through Louisiana French.',
           'It is central to Louisiana geography and culture.',
           'The family fished on the bayou behind the house.'),
 'goober': ('The word comes from a Central African language, as documented by linguist Lorenzo Turner.',
            'It is a good example of an African-origin word in everyday American English.',
            'He bought a bag of boiled goobers at the roadside stand.'),
 'gumbo': ('The word is related to Bantu words for okra.',
           'The dish is one of the best-known African contributions to American food.',
           'The restaurant is famous for its seafood gumbo.'),
 'cooter': ('The word is thought to derive from a West African word for turtle.',
            'It is used in the Southern United States, often in Gullah Geechee speech.',
            'A cooter sat on the log in the pond.'),
 'haint blue': ('The tradition is associated with Gullah Geechee culture in the Lowcountry.',
                'The color is now a popular choice in Southern design.',
                'The porch ceiling was painted haint blue.'),
 'binya': ('The terms are Gullah expressions that describe belonging.',
           'They are used in discussions of island communities.',
           'Locals called the long-time residents binya, and the new arrivals comya.'),
 'plat-eye': ('Stories about the plat-eye warn travelers away from marshes and woods.',
              'It is a distinctive example of Gullah folklore.',
              'Grandmother warned the children about the plat-eye near the creek.'),
 'tabby': ('The material was used in coastal homes and forts in the Lowcountry.',
           "It is important to the region's architecture.",
           'The old ruins were built from tabby.'),
 'camper': ('The term became familiar in early online shooters of the 1990s and is still used in complaints about opponents.',
            'Opinions about camping differ, since some players call it smart tactics and others call it cheap.',
            'The camper in the corner picked off three of us before we noticed.'),
 'noscope': ('The term comes from first-person shooter culture and gave rise to a whole style of trick-shot videos.',
             'It became a meme and a symbol of showy skill in the 2010s.',
             'He landed a noscope across the whole map and the lobby went silent.'),
 'peek': ('The term is central to tactical shooters such as Counter-Strike.',
          'It is a basic skill that separates careful play from rushing in.',
          'He peeked the doorway and spotted two enemies on the stairs.'),
 'rush': ('The term appears in real-time strategy and tactical shooters.',
          'It is a risky tactic that depends on surprise and speed.',
          'They rushed the bomb site in the first ten seconds.'),
 'flank': ('The word comes from military language and appears in nearly every team shooter.',
           'It is a common call-out in voice chat.',
           'Two of us will flank through the tunnel while you hold the front.'),
 'wallhack': ('The term is used in anti-cheat discussions across competitive shooters.',
              'Accusations of wallhacks are common and often unproven.',
              'The way he tracked us through the wall made everyone suspect a wallhack.'),
 'aimbot': ('The term is used across shooter communities and platform policies.',
            'Its use leads to bans in most online games.',
            'He was banned for using an aimbot in ranked matches.'),
 'smurf': ('The term emerged in the 1990s and 2000s in competitive gaming, with the name linked to the cartoon characters.',
           'It frustrates new players and is discouraged by many developers.',
           'There was a smurf in our lobby who finished with forty kills.'),
 'boosting': ('The practice is widespread and is forbidden by most game rules.',
              'It can lead to account suspension.',
              'He lost his account after paying someone for boosting.'),
 'nerf': ('Nerf comes from the foam toy brand, and buff comes from the idea of making something stronger.',
          'The words are now used outside games for any adjustment in strength.',
          'The developers nerfed the shotgun after players complained.'),
 'meta': ('The word is short for metagame, meaning the game outside the game.',
          'It changes with patches and tournament results.',
          'The new meta favors fast characters with short cooldowns.'),
 'op': ('The abbreviation is common in forums and chat.',
        'Players use it as both complaint and compliment.',
        'That new rifle is OP and everyone is using it.'),
 'elo hell': ('The phrase refers to the Elo rating system used in chess and adapted by many games.',
              'Players debate whether the idea is real or an excuse.',
              'He insisted he was in Elo hell even though he kept losing the same way.'),
 'hardstuck': ('The word combines hard and stuck and is common in ranked communities.',
               'It can describe real frustration or just a joke.',
               'She has been hardstuck in silver for six months.'),
 'diff': ('The term is short for difference and became a standard competitive taunt.',
          'It is often used in the phrase jungle diff or support diff.',
          'Our top laner took it as a personal insult when someone said he was getting diffed.'),
 'afk': ('The abbreviation comes from early chat rooms and online games.',
         'It is used to explain absences and to describe inactive teammates.',
         "I'm going AFK for five minutes to grab food."),
 'noob': ('The word comes from newbie, with the spelling n00b appearing in leetspeak.',
          'It can be affectionate or hostile depending on tone.',
          "Don't worry about being a noob, everybody starts there."),
 'respawn': ('The word is from spawn, meaning to appear, and is a basic term in online shooters.',
             'It also appears in everyday speech as a joke about starting over.',
             "We'll respawn in ten seconds and push back."),
 'spawn camping': ('This tactic is widely considered poor sportsmanship.',
                   'Developers add protection systems to prevent it.',
                   'The other team spawn camped us for the whole second half.'),
 'gank': ('The term is popular in MOBAs and MMOs and comes from gang kill.',
          'It is a core tactic in games such as League of Legends and Dota 2.',
          'The jungler came out of the brush and ganked the top lane.'),
 'jungle': ('The term is part of the structure of MOBA maps.',
            'It is a demanding role that requires map awareness.',
            'He plays jungle and always knows where the enemy is.'),
 'inting': ('The word is short for intentional feeding and is common in League of Legends.',
            'It is a bannable offense in ranked play.',
            'He was inting so badly that we asked the support to report him.'),
 'feeding': ('The term is common in MOBA communities.',
             'It can be intentional or the result of bad play.',
             'The mid laner kept feeding and the match was over by twenty minutes.'),
 'mid or feed': ('The phrase became a meme from the culture of lane arguments.',
                 'It shows how competitive pressure creates catchphrases.',
                 'He shouted mid or feed in champion select and everyone sighed.'),
 'macro': ('The term comes from strategy games and is used in MOBA analysis.',
           'Good macro often matters more than flashy mechanics.',
           'Their macro was perfect, so they won without a single teamfight.'),
 'micro': ('The term is central to real-time strategy games such as StarCraft.',
           'Professional players are praised for the speed of their micro.',
           'His micro with the stalkers saved the whole army.'),
 'tank': ('The role appears in most MMOs and many team games.',
          'Its name is also used as a metaphor for someone taking the hit.',
          "I'll tank the boss while you stay behind me."),
 'dps': ('The abbreviation appears in every MMO and many shooters.',
         'It is part of the classic trio of tank, healer, and DPS.',
         'We need one more DPS before we can start the raid.'),
 'healer': ('The role is crucial in MMOs and often has the pressure of keeping everyone alive.',
            'It is both admired and blamed when a raid goes wrong.',
            'Our healer kept us alive through three phases.'),
 'aggro': ('The term describes who an enemy is targeting.',
           'It is used in daily speech for attracting trouble.',
           'The tank pulled aggro just in time.'),
 'raid': ('The term is central to MMOs such as World of Warcraft.',
          'Raids require schedules, roles, and preparation.',
          'Our guild runs a raid every Thursday night.'),
 'wipe': ('The term is common in raiding and dungeon crawling.',
          'It prompts jokes about groups coordinating again.',
          'We wiped on the final boss six times in a row.'),
 'pug': ('The abbreviation is used in MMOs and team games.',
         'The quality of a pug varies widely.',
         'I got stuck with a pug that kept arguing about loot.'),
 'grind': ('The word spread beyond games to describe any repetitive hard work.',
           'It has a positive meaning in hustle culture.',
           'I spent the weekend grinding to reach level fifty.'),
 'loot': ('The word is a staple of role-playing games.', 'Its randomness fuels much of the excitement.', 'The boss dropped a rare piece of loot.'),
 'rng': ('The abbreviation describes the role of randomness in drops and critical hits.',
         'Players use it as an explanation for unlucky outcomes.',
         'The drop rate is pure RNG, so keep trying.'),
 'ult': ('The abbreviation appears in games such as Overwatch and League of Legends.',
         'Its charge time is a key part of strategy.',
         'He saved his ult for the final fight.'),
 'cooldown': ('The term is basic game design vocabulary.',
              'It is also used jokingly outside games, for example when someone needs a break.',
              'My phone is on cooldown after that long call.'),
 'kiting': ('The technique is common in MMOs and MOBAs.',
            'The word comes from flying a kite at a distance.',
            'The hunter kited the monster around the pillar for minutes.'),
 'git gud': ('The phrase grew in online forums and became associated with the Dark Souls community.',
             'Its tone can be teasing or hostile.',
             'The boss kept killing him, and the chat just said git gud.'),
 'you died': ('The screen became an icon of the soulslike genre.',
              'It appears in memes about failure.',
              'He stared at the You Died screen for the tenth time.'),
 'bonfire': ('The item became a symbol of the series.',
             'Players use the word to mean a safe place.',
             'We rested at the bonfire before the next boss.'),
 'neutral': ('The term is central to fighting game analysis.',
             'Players say they are playing neutral when they are probing for an opening.',
             'His neutral was so good that he never had to take risks.'),
 'footsies': ('The term is used in games such as Street Fighter.',
              'It is one of the most important skills in the genre.',
              'The match turned into a long game of footsies.'),
 'whiff punish': ('The term describes a core tactic in fighting games.',
                  'It rewards patience and attention.',
                  'He read the big swing and landed a whiff punish.'),
 'okizeme': ('The word is Japanese for wakeup and is shortened to oki.',
             'It is a central part of fighting game strategy.',
             'His oki setups were so strong that the opponent could not stand up.'),
 'mix-up': ('The term applies to high and low attacks, throws, and strikes.',
            'It adds psychological pressure to the game.',
            'The mix-up left the opponent guessing between a throw and a low strike.'),
 'zoning': ('The term describes a playing style in many fighting games.',
            'It is a source of frustration for close-range characters.',
            'His zoning kept me out of range all round.'),
 'frame data': ('The term is part of competitive fighting game study.',
                'Players memorize them to know what is safe.',
                'I studied the frame data to see which moves were punishable.'),
 'rollback netcode': ('The approach was popularized by the GGPO software created by Tony Cannon in 2006.',
                      'It is a standard demand in modern fighting games.',
                      'Everyone was thrilled when the new game launched with rollback.'),
 'button masher': ('The term is used to describe beginners.',
                   'It is sometimes meant as an insult and sometimes as a compliment about unpredictability.',
                   'He beat me by mashing buttons, which was somehow worse.'),
 'any percent': ('The category allows glitches and shortcuts.',
                 'It is the most common category in speedrunning.',
                 'His any percent run beat the old record by two seconds.'),
 'glitchless': ("The category rewards precise play within the game's intended rules.",
                'It often produces long and careful runs.',
                'The glitchless run took three hours and was a joy to watch.'),
 'rta': ('The term is used in many speedrunning communities.', 'It differs from in-game time.', 'The leaderboard ranks runs by RTA.'),
 'tas': ('The format produces results that would be impossible for a human.',
         'It is a separate category from live runs.',
         'The TAS completed the game in minutes.'),
 'pb': ('The abbreviation is common in speedrunning, running, and lifting.',
        "It is the most celebrated number in a runner's life.",
        'She finally beat her PB on the final stage.'),
 'sequence break': ('The term is used in speedrunning and game design.',
                    'It can reveal hidden paths and secrets.',
                    'The run used a sequence break to skip half the dungeon.'),
 'frame perfect': ('The term describes the hardest tricks in a run.',
                   'It often takes hundreds of attempts.',
                   'He landed the frame perfect jump on his fourth hour of trying.'),
 'games done quick': ('The events began in 2010 with Awesome Games Done Quick.',
                      'They made speedrunning a mainstream spectator event.',
                      'The marathon raised millions of dollars for charity.'),
 'obby': ('The word is short for obstacle and refers to a popular genre of Roblox games.',
          'Players use it to describe any obstacle course.',
          'We spent the night trying to finish a difficult obby.'),
 'robux': ('The currency can be bought with real money and earned by creators.',
           "It is a major part of the platform's economy.",
           'She saved her Robux to buy a new outfit.'),
 'tycoon': ('The term is used widely in Roblox and other simulation games.',
            'It often involves clicking and upgrading.',
            'The kids built a pizza tycoon in a few hours.'),
 'creeper': ('It became a symbol of the game and a meme with the phrase aw man.',
             'The term is used outside the game as a joke.',
             'A creeper blew up the whole wall of the house.'),
 'redstone': ('The system allows players to build machines and calculators.',
              'It is admired as an engineering feature.',
              'He built a working elevator using redstone.'),
 'griefing': ('The term is common in Minecraft and many online games.',
              'It is considered a serious offense on most servers.',
              'A griefer destroyed our shared base overnight.'),
 'victory royale': ("The phrase became part of popular culture after the game's rise in 2017.",
                    'It appears in memes and celebration.',
                    'We finally got a Victory Royale after two hours of trying.'),
 'zero build': ('The mode was introduced in 2022 and attracted players who found building too difficult.',
                'It changed the strategy of the game.',
                'He switched to Zero Build because he never mastered building.'),
 'whale': ('The term comes from casino culture, where whales are the biggest gamblers.',
           'Developers often depend on whales for revenue.',
           'A single whale paid for the entire event.'),
 'gacha': ('The word comes from a Japanese capsule toy machine called gachapon.',
           'Critics compare it to gambling.',
           "He spent a month's savings on gacha pulls."),
 'pay to win': ('The term is used as a criticism in many communities.',
                'Developers sometimes deny it while players disagree.',
                'The game turned pay to win after the update.'),
 'loot box': ('The mechanic has drawn legal scrutiny in several countries.',
              'It is a main subject of debates about gambling.',
              'Parents complained about the loot boxes in the new game.'),
 'simlish': ('The language was created for the series in 2000 and has featured real songs recorded in it.',
             'Fans love learning its phrases.',
             'The characters spoke in Simlish while cooking.'),
 'plumbob': ('It is a symbol of the game and a source of memes.',
             'It shows who the player controls.',
             'The plumbob turned red when his mood dropped.'),
 'bells': ('The series has used the term since 2001.', 'The currency is a charming part of the game.', 'She sold fruit for ten thousand bells.'),
 'turnip stalk market': ('Players buy turnips on Sunday and sell them during the week for profit.',
                         'The system became a meme during 2020.',
                         'He made a fortune on the turnip stalk market.')}

EXAMPLES = ['My cousin be coaching the rec league every Saturday, rain or shine.',
 'They already outside waiting on us.',
 'She done told you twice already, so the answer is not changing.',
 'He BEEN had that car, long before the neighborhood changed.',
 "I'm finna head to the store if anybody needs anything.",
 "Ain't nobody told me the schedule changed this morning.",
 "We didn't see nobody leave the building after the alarm.",
 'My sister stay asking me for my charger.',
 "Don't come acting like you didn't see the message.",
 'He steady talking while the whole room is trying to listen.',
 "I'm about to aks the front desk if they got a spare room.",
 'My uncle work two jobs and still make it to every game.',
 "It's three people already waiting outside the door.",
 "That's Marcus mama calling right now.",
 "I'm bouta pull up if the traffic lets up.",
 'Ion think the store opens until noon on Sunday.',
 'We had walked in and the whole place went quiet.',
 "You can bring the chairs, and I'll handle the speakers, bet.",
 'That story sounds like cap, because nobody saw it happen.',
 'The new pizza spot is the best in town, no cap.',
 'The block party was lit from the first song to the last.',
 'That new playlist opener slaps every single time.',
 'His verse on that track was fire from the first bar.',
 'He walked in with so much drip that the cameras turned around.',
 "I'm taking bae to dinner after the concert.",
 "He's still salty that nobody picked his song.",
 'She brought a full banner and confetti for a casual lunch, which is so extra.',
 'He commented on every single post, which was a little thirsty.',
 'Her clapback to the rumor had everyone reposting it within the hour.',
 'He told us to stay woke about how the new policy would affect the neighborhood.',
 'Once the weather turns, the group chat starts talking about cuffing season.',
 "I'm not lying, on god, the bus was already gone.",
 "That peach cobbler was bussin, and I'm going back for more.",
 'We finished the tournament undefeated, gang gang.',
 'The comment section turned into a wall of opps after the rivalry post.',
 "You must be tweaking if you think I'm walking that far.",
 'Why are you so pressed about who sat in the front row.',
 "He's been boo'd up since the summer and hardly texts back.",
 'Chile, the line at that place was out the door.',
 "I have the receipts from when she said she'd be there.",
 'He said he was home sick, but he was caught in 4K at the mall.',
 'Lemme find out you ate the last slice without telling anybody.',
 'That video of the cat sliding off the table has me weak.',
 "It's the way he paused before the punchline for me.",
 'The decision is made, periodt.',
 'The crowd got me gassed before I even stepped on stage.',
 "Y'all keep gassing me up for a haircut I haven't gotten yet.",
 "He's busy this month because he's trying to secure the bag before school starts.",
 'He flexed his new sneakers in every group photo.',
 "If you're hungry, pull up and we'll cook something.",
 'He walked into the gym with a lot of swag and a brand-new bag.',
 'The coach gave each player a dap as they left the court.',
 "Word, I'll meet you at the corner after class.",
 'That mural on the side of the building is dope.',
 'The remix was def from the first beat.',
 'That beat was phat, and the room knew it.',
 'She walked in looking fly from head to toe.',
 "We're meeting at my crib before the game.",
 'His chain had so much bling that people noticed it from across the room.',
 'He flashed a gold grill when he smiled at the camera.',
 'The new drummer kept everything cool even when the tempo changed.',
 'He always knew the hip places before they got crowded.',
 'That drummer is so bad, he makes the whole song feel alive.',
 'The line at the bakery is mad long today.',
 'Deadass, I left my keys on the counter ten minutes ago.',
 'Pass me that jawn on the table, the blue one.',
 'The whole street turned hyphy the moment the car stereo came on.',
 'The crowd went dumb as soon as the bass dropped.',
 'There were hella people at the market this morning.',
 'Mane, you should have seen the lines at the car show.',
 'He drove his slab down the avenue with the trunk music playing.',
 'His story felt trill because he never tried to impress anyone.',
 'The stadium got crunk when the home team scored the final point.',
 'We were turnt before the first song even finished.',
 'The trap beat on that song has a rolling bass line that shakes the car.',
 'The dorm room looked like a bando after finals.',
 'The late night playlist was all screwed and chopped, slow and heavy.',
 'The block party had a go-go band that kept the crowd moving for hours.',
 'The group chat got a little ratchet when the argument started.',
 'He ordered the fancy tea and said it was too bougie for him.',
 'What it do, everybody, thanks for coming out tonight.',
 'We can kick it at the park until the sun goes down.',
 'Bruh, that cannot be the final score.',
 "I'm picking up my boo from the airport tonight.",
 "Don't pay attention to the haters, just keep doing the work.",
 'My squad is already in line for the concert.',
 "He's my homie from the old neighborhood.",
 'She joined the house when she was nineteen and has treated it like family since.',
 'The house mother organized a fundraiser for a member who needed a safe place to stay.',
 'The category for the night was executive realness, so everyone arrived in tailored suits.',
 'She won the category because her realness was so convincing the judges did not speak.',
 'He is walking three categories tonight and has been practicing for weeks.',
 'He dropped into a vogue pose at the edge of the dance floor.',
 'Her vogue femme performance had judges leaning forward in their seats.',
 'He trained in old way first and then learned the faster new way patterns.',
 'The duckwalk down the runway drew cheers from the crowd.',
 'The performance ended with a death drop that shook the front rows.',
 'She walked in serving elegance and the whole room noticed.',
 'The kiki ball on Friday was full of first-time walkers.',
 'He earned legendary status after years of winning categories in several cities.',
 'She threw shade at the contestant without mentioning her name.',
 'The reading was so precise that the room stopped to listen.',
 'She finally spilled the tea about the surprise party.',
 'You slayed that presentation from the first slide.',
 'Her outfit was snatched from the earrings down to the shoes.',
 'He ate that performance and left no crumbs.',
 'Yasss, that is exactly the outfit for tonight.',
 "I'm gagging over how good that choreography looked.",
 'When the final scene came on, my wig was gone.',
 "It's giving old money with that cardigan and tote.",
 'That entrance was sickening in the best possible way.',
 'Hunty, you have to see what just happened.',
 'She sashayed across the stage with the crowd cheering.',
 'After the lip sync she heard shantay and burst into tears.',
 'He stepped onto the floor and the crowd yelled werk.',
 'When she turned around the audience went purr.',
 'He walked up with so much rizz that the whole table went quiet.',
 "I'm applying the Fanum tax to your fries before you start eating.",
 'He just said gyatt in the middle of the science lesson and the whole class laughed.',
 'Chat, did you see what he just did to that boss fight?',
 'When the final shot landed, the chat filled with Ws.',
 'The streamer missed the jump, and chat sent a wall of Ls.',
 "I'll take the L on that one and pay for lunch.",
 'That reaction was so funny that chat shouted clip it.',
 "He's streaming eight hours a day because he wants to secure the bag.",
 "The coach was mic'd up, and the fans got every word of the pep talk.",
 'Half the fun of the night was talking in the lobby before the match.',
 "That last round was close, so let's run it back.",
 'That boss was light work after we found the weak point.',
 'I got clapped in the first round and had to wait for the next bracket.',
 "If the final boss has a second phase, we're cooked.",
 'That kid is cracked at this game, and he is only twelve.',
 'Every lobby tonight was sweaty, so we switched to a private match.',
 "He's a tryhard in every single match, even the practice games.",
 'He cheesed the final round by repeating the same attack.',
 'After the loss, he asked for a salty runback right away.',
 'He kept calling the other player cheap, which is classic scrub behavior.',
 'They set up a money match at the arcade after the tournament ended.',
 'He saved his pocket character for the final round.',
 "After school he'd log into the Park and run a few games.",
 'Our squad is practicing for the next Pro-Am season.',
 'He kept getting green releases from the corner.',
 'He spent a week grinding for the badge he wanted.',
 'We got the dub in overtime.',
 'We said gg after the match and agreed to a rematch.',
 'The other team typed gg ez, so we muted the chat.',
 'I would have won, but the lag made me miss the dodge.',
 'His ping spiked to three hundred right when the match started.',
 'She carried the whole squad through the final level.',
 'He hit the clutch play with two seconds left.',
 'After three losses in a row, he was on tilt.',
 'That new character looks mid compared with the old one.',
 "Y'all are welcome to come over after the game.",
 "I want all y'all to pick a plate before the food goes cold.",
 "I'm fixin' to leave for church if you want a ride.",
 'We might could finish the quilt by Sunday.',
 'He tried to fix the sink himself, bless his heart.',
 "I reckon it's going to rain before supper.",
 'The barn is right over yonder past the fence.',
 'He asked what kind of coke I wanted, and I said Dr Pepper.',
 'Grab a buggy and meet me at the produce section.',
 'He grew up in a holler where everyone knew the neighbors.',
 "That dadgum car won't start again.",
 'The picture frame is cattywampus on the wall.',
 'We eat supper at six, after the chores are done.',
 "I'll be there directly, after I finish this call.",
 'He offered to carry me to the station.',
 'Mash the elevator button, since it never responds the first time.',
 'He threw a hissy fit when the printer jammed.',
 'She was fit to be tied when she heard the news.',
 'Thanks for waiting, sugar, your order will be right up.',
 "Yes, sir, I'll have it ready by morning.",
 'He pert near finished the whole pie by himself.',
 'They went a-hunting at first light.',
 "I'm plumb worn out from the day's work.",
 "It's a right smart walk from the road to the creek.",
 'She carried the apples home in a poke.',
 'He totes water up the hill every morning.',
 'The fence post was sigogglin after the storm.',
 "The young'uns are playing out in the yard.",
 "How's the crop? Fair to middlin' this year.",
 'Ope, let me just squeeze past you here.',
 "I'll grab a pop from the cooler on the way out.",
 'Uff da, that was a lot of snow overnight.',
 'She brought a tater tot hotdish to the potluck.',
 'Are you coming Saturday? You betcha.',
 "It's going to be a cold one tonight, dontcha know.",
 "He's a proud Yooper and he never goes anywhere without a warm coat.",
 'She stopped for a drink at the bubbler.',
 'Turn left at the stop and go light by the gas station.',
 "We're driving to the cities for the weekend.",
 'They have a cabin up north that the whole family uses in summer.',
 'She said that might be a challenge, which in Minnesota nice meant no.',
 'We went to the supper club for the Friday fish fry.',
 'That clam chowder was wicked good.',
 'We stopped at the packie before the party.',
 'He ordered a chocolate frappe with extra whipped cream.',
 'She put rainbow jimmies on the ice cream cone.',
 'Take the second exit at the rotary.',
 'I took the T to the game and it was packed.',
 'He grabbed a coffee and a bacon egg and cheese from the bodega.',
 'The neighbors sat on the stoop and watched the street.',
 'We waited on line for an hour to get the sandwich.',
 'He asked for a regular coffee and a roll.',
 'Youse should come over for dinner on Sunday.',
 'That jagoff cut me off in the parking lot.',
 'Yinz coming to the game this weekend?',
 'The neighbor is nebby but she means well.',
 "We had some pierogies and kielbasa n'at.",
 'I need to redd up the living room before they arrive.',
 'Hand me a gumband for these papers.',
 "We're going down the shore for the weekend.",
 'Can I get you some coffee, hon?',
 'We picked up a hoagie for lunch.',
 'That wave was gnarly, and we all knew it.',
 "I'm so stoked for the trip this weekend.",
 "That skate park is rad, and it's free.",
 'I got stuck on the 405 for an hour.',
 'There was hecka traffic on the bridge.',
 'The elevator is so janky I take the stairs.',
 'I was like, wait, did that actually happen?',
 'That cafeteria food is so bad, gag me with a spoon.',
 'That call from the referee was totally bogus.',
 'They went up to the mountain to shred all day.',
 'The ramp looked huge, but he said just send it.',
 'He wore all the gear but looked like a kook on the first wave.',
 'The groms were out early, practicing their turns.',
 "It's a sunny day, so the mountain is out.",
 'She said the Seattle freeze made it hard to make friends at first.',
 'The sandwich was dank and so was the playlist.',
 'Bro, you will not believe what happened in lab today.',
 "Dude, that was the best sandwich I've ever had.",
 'The guy at the gym was a total Chad with an impressive routine.',
 'He finally landed his first ollie over the curb.',
 'She spent the afternoon practicing her kickflip.',
 'He bailed on the trick just before landing.',
 'She had an emo phase with studded belts and long bangs.',
 'He was a scene kid in high school with brightly dyed hair.',
 'The goth club had a night with only classic songs.',
 "He's a total normie who only watches mainstream shows.",
 'She burst into song in the hallway because she is a theater kid.',
 'He wore the label redneck with pride on the back of his truck.',
 "He's a good ol' boy who knows everyone in the county.",
 "Hold my beer, I'm going to jump the creek.",
 'We tailgated for four hours before kickoff.',
 "You've been arguing in the comments all day, so go touch grass.",
 'His take is so chronically online that nobody offline would understand it.',
 'I stayed up doomscrolling instead of sleeping.',
 'His old posts are painful and so cringe.',
 "That's just cope, since the results speak for themselves.",
 'Cope and seethe about the final score.',
 'The crowd all repeated the same line like NPCs.',
 'She walked down the street with so much main character energy.',
 "I'm delulu enough to believe the tickets will still be available.",
 'He chewed with his mouth open and gave me the ick.',
 "We've been in a situationship for months with no clear label.",
 'Canceling plans every week is a red flag.',
 'He remembered my allergies, which is a green flag.',
 'She said gaslight gatekeep girlboss while closing the laptop.',
 'Grabbing coffee turned into a side quest across town.',
 'He has so much lore from his college years.',
 "I'm in my study era, so I can't go out tonight.",
 'Her room is pure cottagecore with plants and soft lamps.',
 'The new apartment passed the vibe check immediately.',
 'He watches so many absurd clips that his brainrot is obvious.',
 'The kids shouted skibidi as a nonsense word during recess.',
 'He claimed to be sigma while eating lunch alone.',
 'That cashier sang at the register, which is so Ohio.',
 'He kept mewing during the entire class photo.',
 'He started looksmaxxing with a new haircut and skincare routine.',
 'He lost a thousand aura when he tripped on the stage.',
 'He was aura farming in the hallway with sunglasses on.',
 'The students all yelled six seven when the teacher said the page number.',
 'He crashed out and quit the group chat.',
 "I'm locked in until finals are over.",
 'He called the chatbot a clanker after it failed the task.',
 'He kept mogging everyone in the group photo.',
 'Her answer was totally based, and everyone clapped.',
 'I stan that band and own all the albums.',
 'His take got ratioed within minutes.',
 'That song lives in my head rent free.',
 "She's been yapping about her trip for an hour.",
 'The video was pure rage bait, built to fill the comments with arguments.',
 'The video used unalive as a replacement word because the platform flags the real term.',
 'The health class had a lesson on seggs education.',
 'The creator posted a video about le dollar bean pride.',
 'He used the corn emoji instead of the actual word to avoid the filter.',
 "Órale, I'll meet you at the corner in five minutes.",
 'Hey, ese, thanks for helping me move the couch.',
 'That vato at the corner shop always saves me a seat.',
 "He's my carnal, so I trust him with my keys.",
 'Chale, I forgot my wallet at home.',
 'No manches, you finished the whole project in one night?',
 'The party was so chido that nobody wanted to leave.',
 'Neta, I thought the concert started at seven.',
 'Wey, did you see the game last night?',
 "Simón, I'm in for the trip on Saturday.",
 'Ahorita voy, which might mean in two minutes or in two hours.',
 'He talks like a total fresa, with brand names in every sentence.',
 'The word naco is rejected by many people because it judges others by class.',
 'I picked up some extra chamba this week at the warehouse.',
 'The chamacos are playing outside until dinner.',
 'The morros ran down the street laughing.',
 'That chavo works at the shop on the corner.',
 "It's a pinche scorching day, and the air conditioning is broken.",
 'She came over with the latest chisme about the neighbors.',
 "We missed the bus, ni modo, we'll walk.",
 'Aguas, the floor is wet!',
 'Ándale, the movie is about to start.',
 'Híjole, that was a close call.',
 'Qué onda, are you coming to the market?',
 "He's buena onda and always makes everybody comfortable.",
 'The new skate park is padre.',
 'That was a gacho thing to say to your friend.',
 'The phone case I bought was chafa and broke in a week.',
 "I don't have the lana for a concert this month.",
 'I only have a bit of feria in my pocket.',
 'We grabbed a couple of chelas after the game.',
 'The chilango on my team always knows the best taquerias.',
 'He called himself pocho with a laugh, and no one corrected him.',
 'He proudly said that he was Chicano and that his grandfather came to the fields.',
 'The student group changed its name to Latine Student Union.',
 'My jefa packed lunch for everyone this morning.',
 'Mija, come eat before the food gets cold.',
 'Trucha, someone is coming around the corner.',
 'He brought his ruca to the family barbecue.',
 'His ranfla gleamed under the streetlights.',
 'Everything is firme, nothing to worry about.',
 'The art show featured a photographer who documented chola style in the 1990s.',
 'The museum had an exhibit on pachuco style and music.',
 "Some of his grandfather's phrases were pure caló from the old neighborhood.",
 "Sale, I'll meet you there at six.",
 'He ran into a homeboy from his old block at the airport.',
 'I was tired. Pero tenía que terminar el trabajo.',
 'I was going to call you pero se me olvidó.',
 'It was a great trip, ¿verdad?',
 'We ate lonche at the diner.',
 'He parked his troca in front of the house.',
 'Where did you parquear the car?',
 'The kids are playing in the yarda.',
 'We need to renew the aseguranza for the car.',
 'Textéame when you get there.',
 'Ellos rentan un apartamento cerca del trabajo.',
 'Vamos a janguear en la playa.',
 'We bought fruit at La Marqueta.',
 'She wore a Boricua flag to the parade.',
 'The poet is a Nuyorican who writes in English and Spanish.',
 'Wepa, the music just started!',
 "He ended the speech with pa'lante.",
 'There was a lot of bochinche about the wedding.',
 'I have to bregar with the paperwork tomorrow.',
 'The concert was chévere from start to finish.',
 "Pana, I'll see you tomorrow.",
 'What is that vaina on the table?',
 'Dime a ver, how is your day?',
 'Qué lo qué, my friend, long time no see.',
 'He has tigueraje and always finds a way.',
 'We took the guagua to the city.',
 'His cousin lives in the yuma now.',
 "Asere, what's going on?",
 'Mano, did you hear the news?',
 'She introduced her jevo to the family.',
 'The cipote ran across the yard.',
 'The concert was so chivo.',
 'Vos sabés cómo llegar, ¿verdad?',
 "He doesn't have enough pisto for the bus.",
 "Cabal, that's what I meant.",
 'Parce, vamos a comer algo.',
 'Qué bacano, that was an amazing trip.',
 'Che, did you see the match?',
 'That jacket is piola.',
 'I have a lot of laburo this week.',
 "Opo, I'll bring the food over right after school.",
 'Kuya, could you help me carry these bags?',
 'Tita Marie always brings the best dessert to our parties.',
 'He came home from the airport with pasalubong for everyone.',
 'I got kilig watching the proposal video.',
 'The puppy was so cute that I felt gigil.',
 'Her caption was a hugot about waiting for someone who never came.',
 'He got a new bike, sana all!',
 "I'm quitting my job, charot.",
 "Let's get coffee and share the chika.",
 'Bes, you have to try this place.',
 'She introduced her jowa to the whole family.',
 'Gora na, the train is leaving.',
 'Lodi, your work is amazing.',
 'That edit was petmalu.',
 "Tara, let's grab something to eat.",
 "Sige, I'll call you later.",
 'Nako, I forgot my keys again.',
 'Susmaryosep, look at the mess in here!',
 "I don't know what the exam will be like, bahala na.",
 'He supports his parents out of utang na loob.',
 "Let's meet na lang at the mall later.",
 'Ewan, ask someone else.',
 'Dạ, I understand.',
 'Chị, could you help me with this form?',
 'She asked ăn cơm chưa as soon as I arrived.',
 'He is Việt Kiều and visits Vietnam each summer.',
 'Trời ơi, that was so close!',
 'He believes that even chores should have a bit of sanuk.',
 'I spilled the water, but she said mai pen rai.',
 "He felt kreng jai and didn't ask for help.",
 'Jai yen, we still have time.',
 'Nyob zoo, how are you today?',
 'Ua tsaug for helping us with the move.',
 'She did aegyo to convince her friend to share dessert.',
 'The final scene was daebak.',
 'Hwaiting, you can do it!',
 'She called her older friend unnie with a smile.',
 'He asked his sunbae for advice about the internship.',
 'That concert was jjang.',
 'Heol, the tickets sold out.',
 'His boss was a kkondae who never listened.',
 'The ajumma at the market gave me extra fruit.',
 'She watches a mukbang while she eats lunch.',
 'He has strong nunchi and can tell when people are tired.',
 'Pali pali, the train is leaving!',
 'Aigoo, you must be exhausted.',
 'Hallyu has made Korean pop culture a global phenomenon.',
 'The shop sells kawaii stationery with tiny animals.',
 'Sugoi, that animation is incredible!',
 'Yabai, the line is huge.',
 'She cheers for her oshi at every show.',
 'He proudly calls himself an otaku.',
 'The kohai bowed to the senpai after practice.',
 'Ganbatte on your exam!',
 'We said itadakimasu before the meal.',
 'His jacket is so kakkoii.',
 'The character evokes moe in many fans.',
 'He says that character is his waifu.',
 'He is a weeb who owns every figurine.',
 'The new anime is an isekai about a student in a fantasy realm.',
 'The heroine is a classic tsundere.',
 'He said that teaching is his ikigai.',
 'That player is yyds.',
 'The office culture felt like involution with endless overtime.',
 'He chose lying flat over an exhausting career.',
 'She said bai lan and stopped worrying about promotions.',
 'The startup was known for 996 hours.',
 'The shop owner called him laowai with a smile.',
 'Aiya, I forgot my umbrella.',
 'Ayi gave us some tea.',
 "He's an ABC who speaks limited Mandarin.",
 'He described his own accent as FOB and laughed.',
 'She received a hongbao from her grandmother.',
 'He used his guanxi to find the job.',
 'He wanted to save mianzi in front of the guests.',
 'Everyone shouted ganbei and raised their glasses.',
 'Her grandmother always asks chi fan le ma first.',
 'M goi, can I get through?',
 'The kids lined up for lai see.',
 'We went for yum cha on Sunday morning.',
 "Yaar, don't worry about it.",
 'Arre, wait for me!',
 'The desi student association hosted a festival.',
 'Aunty gave us tea and snacks.',
 'They fixed the fan with a bit of jugaad.',
 'Watching reruns is my timepass.',
 "Let's prepone the meeting to tomorrow.",
 'Bhai, come over.',
 'Didi helped me with homework.',
 'She is bindaas and never worries.',
 'The film was paisa vasool.',
 'The food was mast.',
 'Kya baat hai, that was beautiful.',
 "That's total bakwaas.",
 "Let's do a quick chai break yaar.",
 'He called himself an ABCD with a laugh.',
 'Pass me da kine over there.',
 'Brah, you coming to the beach?',
 'Shoots, see you at six.',
 "I'm pau with work for the day.",
 'That plate lunch was ono.',
 "Let's go get some grindz.",
 'We had choke fun at the party.',
 'We sat on the porch to talk story.',
 'She is so akamai with computers.',
 "You're lolo if you think that will work.",
 "The area is kapu, so don't enter.",
 'We meet at pau hana for drinks.',
 'Howzit, brah?',
 'He gave me a shaka from the car.',
 'Ohana means nobody gets left behind.',
 'We shared some pupu before dinner.',
 'The crowd shouted hana hou.',
 'I left my slippahs at the door.',
 'That kolohe boy hid my keys.',
 "This place is mo' bettah than the last one.",
 "No can, I'm busy tonight.",
 'Bumbye we go.',
 'He spent his weekends at the PC bang playing StarCraft.',
 'That player is a gosu.',
 'He is a wibu with a shelf of posters.',
 'Wah gwaan, my friend, long time no see.',
 'The beach was irie and the music was perfect.',
 'She grew up in New York but spends every summer back a yaad.',
 "Give me a likkle time and I'll be there.",
 'There was nuff food at the party.',
 'The pickney are playing in the yard.',
 'Bredda, can you give me a ride?',
 'The dutty beat made the crowd move.',
 'The band mashed up the stage with a huge performance.',
 'The weekend bashment lasted until dawn.',
 'Big up to everybody who came out tonight.',
 "Bless up, I'll see you tomorrow.",
 'Come nyam some rice and peas with us.',
 'The old house is said to be full of duppies.',
 'The DJ told us to tun up.',
 "Let's link up at the park later.",
 'He said soon come, which meant an hour at least.',
 'Mi cyaan believe it.',
 'Unu come help me with this.',
 'The rude boy look included a sharp suit and hat.',
 'We went to lime at the beach after work.',
 'The weekend fete was packed.',
 'She learned to wine at her first carnival.',
 'Doh worry about it.',
 "It's hot today, ent?",
 'There was bacchanal at the fete last night.',
 'Stop mamaguying me and tell me the truth.',
 'She let out a long steups when he said that.',
 'He has tabanca since she left.',
 'The children told jumbie stories at night.',
 'Wuh loss, I forgot my keys.',
 'Whappen, how are things?',
 'Sak pase, my friend?',
 'Nap boule, thank you.',
 'The kompa band played all night.',
 'Abeg, give me a moment.',
 'No wahala, we can fix it.',
 'I have a gist for you about the wedding.',
 'Many of my friends decided to japa this year.',
 "I can't go out because of sapa.",
 'Oga, can we have a table?',
 'We attended an owambe on the weekend.',
 'Come and chop some jollof rice.',
 'I vex for what he said.',
 'I sabi the way.',
 'Wetin you dey do?',
 "Oya, we're going to be late.",
 'The pikin is sleeping.',
 'The DJ dropped some gbedu.',
 "Charley, let's go.",
 'There will be yawa if we miss the bus.',
 'Sasa, how are you?',
 'Poa, thanks.',
 'Niaje, bro?',
 'Manze, that was crazy.',
 'The braai was lekker.',
 'Eish, that was close.',
 'We had a braai on Sunday.',
 "I'll be there now now.",
 'The club played amapiano all night.',
 'The team lives by ubuntu.',
 "Wagwan, how's your day?",
 'That dinner was peng.',
 'There were bare people at the event.',
 "Allow it, we're not going.",
 "He's a wasteman who never helps.",
 'The mandem are all coming.',
 'He dressed like a roadman in a tracksuit.',
 'I grew up in these ends.',
 "That's peak, the bus just left.",
 'That walk is long.',
 'That lie was bait.',
 "I'm buzzin for the weekend.",
 'He felt mugged off by the cancellation.',
 'Skeen, thanks for explaining.',
 'That song is a mad ting.',
 "Blud, that's wild.",
 'Bruv, pass the ball.',
 "Oh my days, I can't believe it.",
 "Safe, I'll see you later.",
 "That's a good song, innit?",
 "I'm chuffed with my results, and so is my whole family.",
 "I'm knackered after a double shift at the restaurant.",
 "I'm skint until the end of the month, so no restaurants for me.",
 'We were gutted when the final goal was disallowed.',
 'That new bakery is mint, and the pies are huge.',
 'The group chat is full of banter about the football results.',
 'Come in for a cuppa and tell me everything.',
 'That novelty tie is completely naff.',
 'The radio sketches of the 1960s made Polari familiar to a mass audience.',
 'Everyone agreed that the new teacher was fit.',
 "It's proper cold this morning, so wear a coat.",
 'Blimey, look at the size of that queue.',
 "He's a decent bloke who always helps the neighbors.",
 "I'm going to grab a quick kip before the match.",
 'We had a cheeky pint after work.',
 'Cheers, mate, I appreciate the lift.',
 'The craic was mighty at the pub after the match.',
 'How are you? Grand, thanks, and yourself?',
 "Don't be such an eejit, you left the keys in the car.",
 'The printer is banjaxed and the deadline is today.',
 'That gig was deadly, and the band played three encores.',
 'He was giving out about the weather all morning.',
 'Pass me that yoke on the shelf there.',
 "He moved to Dublin for work, but he's a culchie at heart.",
 "Sláinte, everybody, here's to a great year.",
 'A wee bit of sugar, please.',
 "It's a braw day for a walk along the shore.",
 'The bairn is asleep, so keep your voice down.',
 "Dinnae fash yourself, we'll be there on time.",
 "D'ye ken what I mean?",
 "It's a dreich Monday morning, so bring an umbrella.",
 'We sat for hours having a good blether.',
 'He walked into the glass door like a total numpty.',
 'Come here for a cwtch, you look cold.',
 'That cake was lush and I want the recipe.',
 'She felt hiraeth every time she heard the old hymn.',
 "He's my butty from the old mining town.",
 'See you this arvo at the beach.',
 'I stopped at the servo for petrol and a pie.',
 'Thanks heaps, that was really kind.',
 "Don't be such a sook, it's only a scratch.",
 'Pack your cozzie for the beach.',
 'Put your thongs on before you go outside.',
 'He drove a ute to work every day.',
 'The comedian joked about the bogan stereotype for ten minutes.',
 "Let's get maccas for lunch.",
 'Is that fair dinkum, or are you pulling my leg?',
 "Yeah nah, I'll pass on dessert.",
 'She took a selfie in front of the harbor.',
 'Chur, bro, I appreciate it.',
 'Is Friday okay? Sweet as.',
 'Where are my jandals?',
 'Pop down to the dairy for milk.',
 "Yalla, we're going to miss the start of the game.",
 'Habibi, come sit with us for dinner.',
 'Wallah, I left the house on time and the bus never came.',
 "We'll see you next weekend, inshallah.",
 'Mashallah, your garden looks wonderful this year.',
 "Khalas, I've heard enough, let's move on.",
 "Yaani, I'm not sure what he wanted from us.",
 'Sahtein, I hope you enjoyed the food.',
 'Tayeb, we can leave right after lunch.',
 'Akhi, thanks for helping with the food drive.',
 'He said bismillah before he took the first bite.',
 'That was so haram, you ate my leftovers without asking.',
 'She wrote 7abibi in the group chat to greet her cousin.',
 'Come here, Sara joon, and sit by me.',
 'Azizam, did you eat anything today?',
 'He insisted on taarof, so the host offered the tea three times.',
 'Jigaram, come here and let me hug you.',
 'Uso, come sit with us at the game.',
 'The palagi visitor asked about the meaning of the tattoo.',
 "He explained that fa'a Samoa guides every family decision.",
 "Don't be so fia poto, you only read the first page.",
 'Malo, thank you for your help.',
 'She wrote alofa on the card for her grandmother.',
 'The church service was full of ofa and music.',
 'Kia ora, welcome to the meeting.',
 'The whanau gathered for the long weekend.',
 'The elder carried a great deal of mana in the community.',
 'She greeted everyone with aroha and a warm smile.',
 'Great mahi on the project this week.',
 'The hui lasted all afternoon.',
 'Skoden, the show starts in ten minutes.',
 'The shop sold shirts with the word NDN in bold letters.',
 'He grew up on the rez and drives back every holiday.',
 'The elders said the ceremony would start on Indian time.',
 'The stand sold frybread with honey at the powwow.',
 'They traveled hours to attend the powwow.',
 "Yá'át'ééh, welcome to the trading post.",
 "Ahéhee' for the ride, we really appreciate it.",
 "Boozhoo, I'm glad to see everyone here.",
 'Miigwech for sharing the story with us.',
 'Tansi, how are you today?',
 'I had to schlep across town with three heavy bags.',
 'It took real chutzpah to ask for a raise on the first day.',
 'He helped everyone move, which makes him a real mensch.',
 'She likes to kvetch about the weather every morning.',
 'We ordered a plate of pickles to nosh on.',
 'Oy vey, the printer jammed again.',
 'The senator spent the evening schmoozing with donors.',
 'Mazel tov on the new apartment!',
 'Her grandmother kvelled when she heard the graduation speech.',
 "I'm such a klutz, I tripped over my own shoelaces.",
 'The shelf was full of tchotchkes from every trip.',
 'A software glitch delayed the whole schedule.',
 'He gave the same spiel to every customer who walked in.',
 'After all that work, we got bupkis.',
 'The holiday travel mishegas started on Wednesday.',
 'His shtick is to answer every question with a joke.',
 'Bubbe baked the challah for the whole family.',
 'The butcher greeted him as paisan and wrapped extra sausage.',
 'Mangia, there is plenty of food on the table.',
 'Keep the noise down after ten, capisce?',
 'Sunday means gravy simmering on the stove all morning.',
 'He ordered a sandwich with gabagool and provolone.',
 "Madonn', look at the size of that line.",
 'The baker slipped in a free cookie as lagniappe.',
 'Come on in, cher, the food is almost ready.',
 'We went to the fais do-do on Saturday night.',
 'The parade began with a cheer of laissez les bons temps rouler.',
 "We're making groceries this afternoon before the storm.",
 'They parked on the neutral ground during the parade.',
 'The second line wound through the neighborhood with umbrellas and horns.',
 "He greeted us with where y'at and a big smile.",
 'The crowd shouted who dat before kickoff.',
 'We passed a good time at the crawfish boil.',
 'The family fished on the bayou behind the house.',
 'He bought a bag of boiled goobers at the roadside stand.',
 'The restaurant is famous for its seafood gumbo.',
 'A cooter sat on the log in the pond.',
 'The porch ceiling was painted haint blue.',
 'Locals called the long-time residents binya, and the new arrivals comya.',
 'Grandmother warned the children about the plat-eye near the creek.',
 'The old ruins were built from tabby.',
 'The camper in the corner picked off three of us before we noticed.',
 'He landed a noscope across the whole map and the lobby went silent.',
 'He peeked the doorway and spotted two enemies on the stairs.',
 'They rushed the bomb site in the first ten seconds.',
 'Two of us will flank through the tunnel while you hold the front.',
 'The way he tracked us through the wall made everyone suspect a wallhack.',
 'He was banned for using an aimbot in ranked matches.',
 'There was a smurf in our lobby who finished with forty kills.',
 'He lost his account after paying someone for boosting.',
 'The developers nerfed the shotgun after players complained.',
 'The new meta favors fast characters with short cooldowns.',
 'That new rifle is OP and everyone is using it.',
 'He insisted he was in Elo hell even though he kept losing the same way.',
 'She has been hardstuck in silver for six months.',
 'Our top laner took it as a personal insult when someone said he was getting diffed.',
 "I'm going AFK for five minutes to grab food.",
 "Don't worry about being a noob, everybody starts there.",
 "We'll respawn in ten seconds and push back.",
 'The other team spawn camped us for the whole second half.',
 'The jungler came out of the brush and ganked the top lane.',
 'He plays jungle and always knows where the enemy is.',
 'He was inting so badly that we asked the support to report him.',
 'The mid laner kept feeding and the match was over by twenty minutes.',
 'He shouted mid or feed in champion select and everyone sighed.',
 'Their macro was perfect, so they won without a single teamfight.',
 'His micro with the stalkers saved the whole army.',
 'He tried a zergling rush, but the opponent had already walled off the base.',
 "I'll tank the boss while you stay behind me.",
 'We need one more DPS before we can start the raid.',
 'Our healer kept us alive through three phases.',
 'The tank pulled aggro just in time.',
 'Our guild runs a raid every Thursday night.',
 'We wiped on the final boss six times in a row.',
 'I got stuck with a pug that kept arguing about loot.',
 'I spent the weekend grinding to reach level fifty.',
 'The boss dropped a rare piece of loot.',
 'The drop rate is pure RNG, so keep trying.',
 'He saved his ult for the final fight.',
 'My phone is on cooldown after that long call.',
 'The hunter kited the monster around the pillar for minutes.',
 'The boss kept killing him, and the chat just said git gud.',
 'He stared at the You Died screen for the tenth time.',
 'We rested at the bonfire before the next boss.',
 'His neutral was so good that he never had to take risks.',
 'The match turned into a long game of footsies.',
 'He read the big swing and landed a whiff punish.',
 'His oki setups were so strong that the opponent could not stand up.',
 'The mix-up left the opponent guessing between a throw and a low strike.',
 'His zoning kept me out of range all round.',
 'I studied the frame data to see which moves were punishable.',
 'Everyone was thrilled when the new game launched with rollback.',
 'He beat me by mashing buttons, which was somehow worse.',
 'His any percent run beat the old record by two seconds.',
 'The glitchless run took three hours and was a joy to watch.',
 'The leaderboard ranks runs by RTA.',
 'The TAS completed the game in minutes.',
 'She finally beat her PB on the final stage.',
 'The run used a sequence break to skip half the dungeon.',
 'He landed the frame perfect jump on his fourth hour of trying.',
 'The marathon raised millions of dollars for charity.',
 'We spent the night trying to finish a difficult obby.',
 'She saved her Robux to buy a new outfit.',
 'The kids built a pizza tycoon in a few hours.',
 'A creeper blew up the whole wall of the house.',
 'He built a working elevator using redstone.',
 'A griefer destroyed our shared base overnight.',
 'We finally got a Victory Royale after two hours of trying.',
 'He switched to Zero Build because he never mastered building.',
 'A single whale paid for the entire event.',
 "He spent a month's savings on gacha pulls.",
 'The game turned pay to win after the update.',
 'Parents complained about the loot boxes in the new game.',
 'The characters spoke in Simlish while cooking.',
 'The plumbob turned red when his mood dropped.',
 'She sold fruit for ten thousand bells.',
 'He made a fortune on the turnip stalk market.',
 'A critic pointed out that nearly every reaction GIF in the thread featured Black faces used by people who were not Black.',
 'The article described how some influencers were accused of blackfishing to attract brand deals.',
 'The comedian ended every sentence with a fake Spanish phrase that drew uncomfortable laughs.',
 'The sketch relied on mock Asian speech, which the audience criticized as lazy and offensive.',
 "The caller's voice was judged before anyone saw the application.",
 'She speaks one way with her family and another way in the interview, and she is tired of the effort.',
 'The way the character talked had been enregistered as a stereotype long before the film.',
 'The raciolinguistics course examined how teachers judge the speech of different students.',
 'The teenagers kept their local pronunciation because it carried covert prestige.']
