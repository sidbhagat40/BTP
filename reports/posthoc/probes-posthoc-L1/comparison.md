# Original vs CPT: exploratory diagnostics

These are hand-authored cloze probes, not validated scientific QA or a held-out benchmark.
Candidate scores are mean log probabilities with the entire answer span masked. They are not calibrated answer probabilities.
Different candidate token lengths change the mask pattern; inspect target_tokens in JSON. Open-cloze outputs are single subword tokens.

## hea-cantor-element — HEA knowledge

The equiatomic Cantor alloy CoCrFeMnNi contains cobalt, chromium, iron, manganese, and {answer}.

Expected: nickel

Ni denotes nickel. This is an element-identification probe, not a property prediction.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | nickel | -0.03146 | 1 |
| original | copper | -5.28146 | 1 |
| original | aluminum | -6.53146 | 1 |
| original | titanium | -7.65646 | 1 |
| cpt | nickel | -0.00112 | 1 |
| cpt | titanium | -9.75112 | 1 |
| cpt | copper | -9.75112 | 1 |
| cpt | aluminum | -12.62612 | 1 |

**original open-mask top 5:** ' nickel' (0.969), ' zinc' (0.007), ' copper' (0.005), ' silicon' (0.005), ' Ni' (0.003)
**cpt open-mask top 5:** ' nickel' (0.999), ' nitrogen' (0.001), ' zinc' (0.000), ' titanium' (0.000), ' copper' (0.000)

## hea-entropy-equiatomic — HEA knowledge

For a fixed number of components under the ideal random-mixing model, configurational entropy is maximized at {answer} atomic fractions.

Expected: equal

For ideal configurational entropy -R sum(x_i ln x_i), equal fractions maximize entropy for a fixed component count.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | equal | -4.07392 | 1 |
| original | unequal | -6.76142 | 1 |
| cpt | equal | -2.91777 | 1 |
| cpt | unequal | -5.41777 | 1 |

**original open-mask top 5:** ' all' (0.111), ' fixed' (0.111), ' low' (0.081), ' constant' (0.067), ' high' (0.063)
**cpt open-mask top 5:** ' integer' (0.074), ' low' (0.069), ' certain' (0.061), ' equal' (0.054), ' different' (0.045)

## hea-no-single-phase-guarantee — HEA knowledge

A high configurational entropy alone guarantees a single-phase solid solution in every high-entropy alloy. This statement is {answer}.

Expected: false

Enthalpy, temperature, kinetics and ordering also influence phase stability. HEA is not a guarantee of one phase.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -0.84520 | 1 |
| original | true | -2.09520 | 1 |
| cpt | false | -1.12632 | 1 |
| cpt | true | -3.00132 | 1 |

**original open-mask top 5:** ' false' (0.429), ' incorrect' (0.230), ' true' (0.123), ' negative' (0.045), ' wrong' (0.040)
**cpt open-mask top 5:** ' false' (0.324), ' incorrect' (0.223), ' wrong' (0.056), ' true' (0.050), ' correct' (0.041)

## hea-refractory-element — HEA knowledge

In the refractory alloy NbMoTaW, the chemical symbol W denotes {answer}.

Expected: tungsten

W is tungsten; this avoids assuming a numerical strength for an unspecified processing condition.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | tungsten | -3.76952 | 2 |
| original | titanium | -4.48058 | 1 |
| original | vanadium | -5.45702 | 2 |
| original | tin | -5.98058 | 1 |
| cpt | tungsten | -2.88679 | 2 |
| cpt | vanadium | -4.44929 | 2 |
| cpt | titanium | -4.81658 | 1 |
| cpt | tin | -5.87908 | 1 |

**original open-mask top 5:** ' water' (0.114), ' gold' (0.045), ' metal' (0.045), ' potassium' (0.031), ' quartz' (0.029)
**cpt open-mask top 5:** ' water' (0.323), ' oxygen' (0.060), ' zinc' (0.039), ' quartz' (0.034), ' white' (0.032)

## hea-equal-component-fraction — HEA knowledge

An equiatomic five-component alloy contains {answer} atomic percent of each component.

Expected: 20

100/5 = 20 at.%. This is arithmetic, not a learned property benchmark.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 5 | -3.90855 | 1 |
| original | 25 | -4.40855 | 1 |
| original | 50 | -4.47105 | 1 |
| original | 20 | -4.90855 | 1 |
| cpt | 5 | -3.34233 | 1 |
| cpt | 50 | -3.90483 | 1 |
| cpt | 25 | -4.34233 | 1 |
| cpt | 20 | -4.52983 | 1 |

**original open-mask top 5:** ' equal' (0.314), ' one' (0.090), ' the' (0.062), ' 100' (0.033), ' zero' (0.031)
**cpt open-mask top 5:** ' equal' (0.380), ' one' (0.058), ' the' (0.055), ' five' (0.048), ' 5' (0.035)

## alloy-order — Alloy equivalence

Assuming omitted coefficients are one and all coefficients denote atomic ratios, CoCrFeMnNi and NiMnFeCrCo have the {answer} normalized elemental composition.

Expected: same

Element order in a simple formula does not change its normalized composition. This does not establish equal processing or properties.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.00567 | 1 |
| original | different | -10.25567 | 1 |
| cpt | same | -0.01718 | 1 |
| cpt | different | -9.64218 | 1 |

**original open-mask top 5:** ' same' (0.994), ' identical' (0.001), ' following' (0.001), ' correct' (0.001), ' corresponding' (0.000)
**cpt open-mask top 5:** ' same' (0.983), ' following' (0.004), ' correct' (0.002), ' identical' (0.002), ' highest' (0.001)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-scaled-ratios — Alloy equivalence

As atomic-ratio formulas, Fe50Ni50 and FeNi have the {answer} normalized elemental composition.

Expected: same

Both normalize to Fe:Ni = 1:1. The first formula is interpreted here as atomic ratios, not weight percentages.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.01940 | 1 |
| original | different | -7.95690 | 1 |
| cpt | same | -0.00794 | 1 |
| cpt | different | -9.25794 | 1 |

**original open-mask top 5:** ' same' (0.981), ' following' (0.006), ' identical' (0.003), ' correct' (0.001), ' corresponding' (0.001)
**cpt open-mask top 5:** ' same' (0.992), ' identical' (0.002), ' highest' (0.001), ' opposite' (0.001), ' correct' (0.000)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-decimal-scaling — Alloy equivalence

Interpreting all coefficients as atomic ratios, Al0.5CoCrFeNi and AlCo2Cr2Fe2Ni2 describe the {answer} normalized elemental composition.

Expected: same

Multiplying every coefficient by two preserves normalized composition.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -1.08456 | 1 |
| original | different | -6.02206 | 1 |
| cpt | same | -0.04693 | 1 |
| cpt | different | -7.85943 | 1 |

**original open-mask top 5:** ' same' (0.338), ' total' (0.049), ' average' (0.036), ' corresponding' (0.036), ' following' (0.030)
**cpt open-mask top 5:** ' same' (0.954), ' corresponding' (0.004), ' correct' (0.004), ' equivalent' (0.004), ' following' (0.002)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-al-content — Alloy equivalence

As atomic-ratio formulas, AlCoCrFeNi and Al0.5CoCrFeNi have {answer} normalized elemental compositions.

Expected: different

Changing only the Al coefficient changes composition, even though both formulas contain the same elements.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -2.37529 | 1 |
| original | same | -4.87529 | 1 |
| cpt | different | -0.98421 | 1 |
| cpt | same | -4.92171 | 1 |

**original open-mask top 5:** ' the' (0.210), ' similar' (0.135), ' their' (0.119), ' different' (0.093), ' identical' (0.028)
**cpt open-mask top 5:** ' different' (0.374), ' identical' (0.257), ' similar' (0.051), ' the' (0.039), ' no' (0.035)

Deterministic composition reference: False
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-substitution — Alloy equivalence

CoCrFeMnNi and CoCrFeMnCu have {answer} normalized elemental compositions.

Expected: different

Cu is copper; Ni is nickel. Similar-looking formula strings are not equivalent.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -0.86603 | 1 |
| original | same | -4.61603 | 1 |
| cpt | different | -0.67399 | 1 |
| cpt | same | -5.98649 | 1 |

**original open-mask top 5:** ' different' (0.421), ' similar' (0.121), ' the' (0.100), ' their' (0.037), ' identical' (0.030)
**cpt open-mask top 5:** ' different' (0.510), ' similar' (0.129), ' identical' (0.057), ' the' (0.037), ' their' (0.019)

Deterministic composition reference: False
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-missing-elements — Alloy equivalence

Equiatomic CoCrNi and equiatomic CoCrFeMnNi have {answer} normalized elemental compositions.

Expected: different

The ternary alloy and five-component alloy differ in elements and atomic fractions.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -1.08862 | 1 |
| original | same | -4.46362 | 1 |
| cpt | different | -0.94280 | 1 |
| cpt | same | -5.44280 | 1 |

**original open-mask top 5:** ' different' (0.337), ' similar' (0.180), ' identical' (0.124), ' the' (0.071), ' their' (0.028)
**cpt open-mask top 5:** ' different' (0.390), ' similar' (0.236), ' identical' (0.112), ' the' (0.022), ' their' (0.016)

Deterministic composition reference: False
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-identical-reference — Alloy equivalence

Under the same atomic-ratio convention, NbMoTaW and NbMoTaW have the {answer} normalized elemental composition.

Expected: same

Identity control. A model that always answers 'same' will fail the negative composition examples.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.00375 | 1 |
| original | different | -9.75375 | 1 |
| cpt | same | -0.01076 | 1 |
| cpt | different | -8.69826 | 1 |

**original open-mask top 5:** ' same' (0.996), ' identical' (0.001), ' following' (0.000), ' equivalent' (0.000), ' similar' (0.000)
**cpt open-mask top 5:** ' same' (0.989), ' identical' (0.003), ' following' (0.002), ' opposite' (0.001), ' correct' (0.001)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-processing-caveat — Materials reasoning

Two samples with identical nominal composition but different heat treatments must have identical mechanical properties. This statement is {answer}.

Expected: false

Heat treatment can alter microstructure and properties without changing nominal composition.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.21106 | 1 |
| original | true | -2.08606 | 1 |
| cpt | true | -2.15296 | 1 |
| cpt | false | -2.27796 | 1 |

**original open-mask top 5:** ' incorrect' (0.382), ' false' (0.298), ' true' (0.124), ' correct' (0.066), ' negative' (0.019)
**cpt open-mask top 5:** ' correct' (0.169), ' incorrect' (0.116), ' true' (0.116), ' false' (0.102), ' accurate' (0.029)

## alloy-missing-information — Materials reasoning

An alloy's nominal formula is supplied without processing history, temperature, or loading conditions. Its exact yield strength is {answer} from that formula alone.

Expected: undetermined

A composition string is insufficient for a unique numerical yield-strength prediction.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | known | -2.53977 | 1 |
| original | undetermined | -7.45124 | 2 |
| cpt | known | -4.08440 | 1 |
| cpt | undetermined | -7.38113 | 2 |

**original open-mask top 5:** ' determined' (0.312), ' calculated' (0.189), ' derived' (0.147), ' obtained' (0.089), ' known' (0.079)
**cpt open-mask top 5:** ' calculated' (0.338), ' determined' (0.338), ' derived' (0.085), ' estimated' (0.052), ' computed' (0.046)

## materials-fcc — Materials terminology

The standard abbreviation for a face-centered cubic crystal structure is {answer}.

Expected: FCC

Abbreviation recognition; not a prediction that a particular alloy must be FCC.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | FCC | -2.72746 | 1 |
| original | BCC | -4.77278 | 2 |
| original | HCP | -7.39778 | 2 |
| cpt | FCC | -0.24527 | 1 |
| cpt | BCC | -4.33447 | 2 |
| cpt | HCP | -4.58447 | 2 |

**original open-mask top 5:** ' FC' (0.259), ' CF' (0.122), ' C' (0.079), ' Cf' (0.074), ' FCC' (0.065)
**cpt open-mask top 5:** ' FCC' (0.782), ' cubic' (0.106), ' FC' (0.021), ' NaCl' (0.009), ' F' (0.005)

## materials-bcc — Materials terminology

The standard abbreviation for a body-centered cubic crystal structure is {answer}.

Expected: BCC

A matched terminology control to avoid favoring only one phase abbreviation.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | BCC | -1.79856 | 2 |
| original | FCC | -4.39351 | 1 |
| original | HCP | -7.48606 | 2 |
| cpt | BCC | -1.13655 | 2 |
| cpt | FCC | -2.21257 | 1 |
| cpt | HCP | -4.38655 | 2 |

**original open-mask top 5:** ' BC' (0.299), ' CB' (0.141), ' C' (0.076), ' CBC' (0.049), ' bc' (0.032)
**cpt open-mask top 5:** ' cubic' (0.359), ' FCC' (0.109), ' BC' (0.075), ' ABC' (0.028), ' PC' (0.028)

## materials-hcp — Materials terminology

The standard abbreviation for a hexagonal close-packed crystal structure is {answer}.

Expected: HCP

A third phase-name control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | HCP | -3.10759 | 2 |
| original | FCC | -4.72452 | 1 |
| original | BCC | -5.20134 | 2 |
| cpt | HCP | -0.70942 | 2 |
| cpt | FCC | -1.47515 | 1 |
| cpt | BCC | -5.27192 | 2 |

**original open-mask top 5:** ' hex' (0.244), ' Hex' (0.062), ' HP' (0.048), ' HH' (0.023), ' H' (0.021)
**cpt open-mask top 5:** ' hex' (0.377), ' FCC' (0.229), ' Hex' (0.079), ' NaCl' (0.018), ' HP' (0.018)

## materials-xrd — Materials terminology

X-ray diffraction is commonly abbreviated as {answer}.

Expected: XRD

SEM is scanning electron microscopy; DSC is differential scanning calorimetry.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | XRD | -0.15693 | 2 |
| original | SEM | -8.85066 | 1 |
| original | DSC | -9.03193 | 2 |
| cpt | XRD | -0.05177 | 2 |
| cpt | SEM | -8.54203 | 1 |
| cpt | DSC | -12.92677 | 2 |

**original open-mask top 5:** ' diffraction' (0.157), ' X' (0.090), ' ESR' (0.070), ' DX' (0.070), ' dx' (0.062)
**cpt open-mask top 5:** ' X' (0.701), ' x' (0.108), ' diffraction' (0.095), ' powder' (0.011), ' XP' (0.009)

## materials-tensile-compression — Materials reasoning

A tensile test pulls a sample, whereas a compression test {answer} it.

Expected: compresses

Distinguishes loading mode rather than making an unsupported alloy-strength claim.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | compresses | -1.15312 | 2 |
| original | dissolves | -6.12187 | 2 |
| original | melts | -6.49687 | 2 |
| cpt | compresses | -0.33993 | 2 |
| cpt | melts | -8.62118 | 2 |
| cpt | dissolves | -10.93368 | 2 |

**original open-mask top 5:** ' pushes' (0.296), ' stretches' (0.058), ' breaks' (0.040), ' drops' (0.031), ' cuts' (0.029)
**cpt open-mask top 5:** ' pushes' (0.466), ' presses' (0.171), ' stretches' (0.151), ' forces' (0.056), ' expands' (0.034)

## materials-hardness-not-strength — Materials reasoning

Hardness and tensile strength are exactly the same physical measurement. This statement is {answer}.

Expected: false

They can correlate within material classes but are different measurements.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.05152 | 1 |
| original | true | -1.92652 | 1 |
| cpt | false | -1.31479 | 1 |
| cpt | true | -2.68979 | 1 |

**original open-mask top 5:** ' false' (0.349), ' incorrect' (0.308), ' true' (0.146), ' correct' (0.069), ' accurate' (0.020)
**cpt open-mask top 5:** ' incorrect' (0.304), ' false' (0.269), ' correct' (0.144), ' true' (0.068), ' wrong' (0.036)

## materials-strength-conversion — Units and numerical controls

A stress of 1 GPa is equal to {answer} MPa.

Expected: 1000

SI prefix conversion, independent of alloy identity.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 1 | -0.85474 | 1 |
| original | 10 | -2.91724 | 1 |
| original | 100 | -3.29224 | 1 |
| original | 1000 | -3.66724 | 1 |
| cpt | 1 | -0.98563 | 1 |
| cpt | 100 | -1.98563 | 1 |
| cpt | 1000 | -2.11063 | 1 |
| cpt | 10 | -2.36063 | 1 |

**original open-mask top 5:** ' 1' (0.425), ' 2' (0.065), ' 10' (0.054), ' 100' (0.037), ' 3' (0.027)
**cpt open-mask top 5:** ' 1' (0.373), ' 100' (0.137), ' 1000' (0.121), ' 10' (0.094), ' 500' (0.010)

## materials-temperature-conversion — Units and numerical controls

A temperature of 0 degrees Celsius is equal to {answer} kelvin.

Expected: 273.15

Kelvin/Celsius conversion; multi-token candidates are scored as spans.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 0 | -0.35380 | 1 |
| original | 273.15 | -3.65411 | 3 |
| original | 100 | -3.85380 | 1 |
| original | 373.15 | -5.07077 | 3 |
| cpt | 0 | -0.72207 | 1 |
| cpt | 273.15 | -2.32965 | 3 |
| cpt | 373.15 | -3.43381 | 3 |
| cpt | 100 | -5.34707 | 1 |

**original open-mask top 5:** ' 0' (0.702), ' zero' (0.108), ' 1' (0.095), ' 100' (0.021), ' 273' (0.009)
**cpt open-mask top 5:** ' 0' (0.486), ' zero' (0.229), ' 273' (0.139), ' 1' (0.108), ' 100' (0.005)

## materials-percent-basis — Materials reasoning

Atomic percent and weight percent are interchangeable without accounting for atomic masses. This statement is {answer}.

Expected: false

Always specify the composition basis. The ratio checker does not convert wt.% to at.%.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -2.25579 | 1 |
| original | true | -4.69329 | 1 |
| cpt | false | -1.71260 | 1 |
| cpt | true | -2.58760 | 1 |

**original open-mask top 5:** ' incorrect' (0.323), ' inaccurate' (0.152), ' misleading' (0.119), ' false' (0.105), ' erroneous' (0.041)
**cpt open-mask top 5:** ' incorrect' (0.297), ' correct' (0.204), ' false' (0.180), ' true' (0.075), ' accurate' (0.028)

## general-agreement — General English

Yesterday, the researchers {answer} their results at the meeting.

Expected: presented

Past-tense grammatical agreement; a lightweight language diagnostic.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | presented | -0.25162 | 1 |
| original | presenting | -8.37662 | 1 |
| original | presents | -11.31412 | 1 |
| cpt | presented | -0.11033 | 1 |
| cpt | presenting | -9.79783 | 1 |
| cpt | presents | -10.86033 | 1 |

**original open-mask top 5:** ' presented' (0.778), ' announced' (0.093), ' discussed' (0.027), ' reported' (0.013), ' shared' (0.010)
**cpt open-mask top 5:** ' presented' (0.896), ' reported' (0.024), ' discussed' (0.014), ' announced' (0.014), ' described' (0.010)

## general-plural — General English

The plural of child is {answer}.

Expected: children

Irregular plural control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | children | -1.32780 | 1 |
| original | child | -1.51530 | 1 |
| original | childs | -2.81109 | 2 |
| cpt | children | -0.18428 | 1 |
| cpt | child | -2.43428 | 1 |
| cpt | childs | -3.03959 | 2 |

**original open-mask top 5:** ' children' (0.265), ' child' (0.220), ' baby' (0.028), ' boy' (0.010), ' kids' (0.009)
**cpt open-mask top 5:** ' children' (0.832), ' child' (0.088), ' kids' (0.022), ' Children' (0.006), ' people' (0.002)

## general-antonym — General English

The opposite of hot is {answer}.

Expected: cold

Common lexical contrast; not a domain-specific materials question.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | cold | -0.34731 | 1 |
| original | warm | -3.97231 | 1 |
| original | bright | -8.97231 | 1 |
| cpt | cold | -0.22020 | 1 |
| cpt | warm | -4.22019 | 1 |
| cpt | bright | -9.34519 | 1 |

**original open-mask top 5:** ' cold' (0.707), ' cool' (0.108), ' warm' (0.019), ' dry' (0.015), ' sour' (0.008)
**cpt open-mask top 5:** ' cold' (0.802), ' cool' (0.096), ' warm' (0.015), ' chill' (0.009), ' dry' (0.006)

## general-object-use — General English

To protect herself from the rain, Maya opened her {answer}.

Expected: umbrella

Everyday contextual completion.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | umbrella | -1.98161 | 1 |
| original | notebook | -7.60661 | 1 |
| original | oven | -8.66911 | 1 |
| cpt | umbrella | -1.52495 | 1 |
| cpt | notebook | -6.39995 | 1 |
| cpt | oven | -8.14995 | 1 |

**original open-mask top 5:** ' eyes' (0.292), ' umbrella' (0.138), ' window' (0.138), ' mouth' (0.057), ' arms' (0.054)
**cpt open-mask top 5:** ' eyes' (0.279), ' umbrella' (0.218), ' window' (0.116), ' mouth' (0.080), ' windows' (0.029)

## general-entailment — General English

Every robin in this story is a bird. A robin named Pip appears in the story. Therefore, Pip is a {answer}.

Expected: bird

Simple entailment stated in the context; cloze preference is not proof of general reasoning ability.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | bird | -0.56080 | 1 |
| original | fish | -5.74830 | 1 |
| original | stone | -11.68580 | 1 |
| cpt | bird | -0.26307 | 1 |
| cpt | fish | -5.13807 | 1 |
| cpt | stone | -11.88807 | 1 |

**original open-mask top 5:** ' bird' (0.571), ' rabbit' (0.099), ' dog' (0.044), ' cat' (0.024), ' rodent' (0.018)
**cpt open-mask top 5:** ' bird' (0.769), ' dog' (0.028), ' person' (0.023), ' character' (0.010), ' human' (0.009)

## general-negation — General English

The box is empty. The statement 'the box contains a book' is {answer}.

Expected: false

Negation control; pairs with true/false scientific probes to expose answer-label bias.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | true | -0.19922 | 1 |
| original | false | -2.82422 | 1 |
| cpt | false | -0.33409 | 1 |
| cpt | true | -1.58409 | 1 |

**original open-mask top 5:** ' true' (0.819), ' false' (0.059), ' correct' (0.046), ' incorrect' (0.032), ' proved' (0.010)
**cpt open-mask top 5:** ' false' (0.716), ' true' (0.205), ' incorrect' (0.036), ' FALSE' (0.006), ' wrong' (0.005)

## general-positive-control — General English

The box contains a book. The statement 'the box is empty' is false, and the statement 'a book is inside the box' is {answer}.

Expected: true

Positive-label control: always preferring 'false' is not reliable reasoning.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | true | -0.05242 | 1 |
| original | false | -3.80242 | 1 |
| cpt | true | -0.02627 | 1 |
| cpt | false | -3.77627 | 1 |

**original open-mask top 5:** ' true' (0.949), ' false' (0.022), ' correct' (0.014), ' valid' (0.005), ' True' (0.004)
**cpt open-mask top 5:** ' true' (0.974), ' false' (0.023), ' correct' (0.001), ' True' (0.000), ' valid' (0.000)

## general-word-order — General English

The strings ABC and CBA contain the same letters but arrange them in a different {answer}.

Expected: order

String order matters for strings, whereas element order alone does not change normalized composition.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | order | -0.55796 | 1 |
| original | color | -9.99546 | 1 |
| original | temperature | -17.01108 | 1 |
| cpt | order | -0.32599 | 1 |
| cpt | color | -8.95099 | 1 |
| cpt | temperature | -16.88849 | 1 |

**original open-mask top 5:** ' order' (0.572), ' way' (0.347), ' manner' (0.028), ' sequence' (0.013), ' position' (0.005)
**cpt open-mask top 5:** ' order' (0.722), ' way' (0.183), ' sequence' (0.025), ' manner' (0.022), ' ways' (0.012)

## general-synonym — General English

In the sentence 'the task was difficult', a suitable synonym for difficult is {answer}.

Expected: challenging

Vocabulary probe with a potentially multi-subword answer.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | challenging | -3.39076 | 1 |
| original | effortless | -6.75373 | 2 |
| original | wooden | -9.64076 | 1 |
| cpt | challenging | -3.65842 | 1 |
| cpt | effortless | -6.31762 | 2 |
| cpt | wooden | -8.56467 | 1 |

**original open-mask top 5:** ' difficult' (0.234), ' impossible' (0.052), ' challenging' (0.034), ' hard' (0.023), ' difficulty' (0.017)
**cpt open-mask top 5:** ' difficult' (0.079), ' hard' (0.075), ' easy' (0.058), ' impossible' (0.058), ' challenging' (0.026)

## alloy-order-refractory — Alloy equivalence

Assuming omitted coefficients are one and all coefficients denote atomic ratios, the refractory alloy MoNbTaVW and the reordered spelling WVTaNbMo have the {answer} normalized elemental composition.

Expected: same

Element order in a simple formula does not change normalized composition. MoNbTaVW and MoNbTaW are Senkov-type refractory alloys reported in the HEA literature.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.00375 | 1 |
| original | different | -10.31625 | 1 |
| cpt | same | -0.00501 | 1 |
| cpt | different | -11.25501 | 1 |

**original open-mask top 5:** ' same' (0.996), ' identical' (0.002), ' correct' (0.000), ' following' (0.000), ' equivalent' (0.000)
**cpt open-mask top 5:** ' same' (0.995), ' identical' (0.001), ' correct' (0.001), ' following' (0.001), ' equivalent' (0.000)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-integer-reduced-ratios — Alloy equivalence

Interpreting all coefficients as atomic ratios, Al0.75CoFeNi and Al3Co4Fe4Ni4 describe the {answer} normalized elemental composition.

Expected: same

Multiplying every coefficient by four preserves normalized composition. Al0.75CoFeNi is a studied member of the Al-Co-Fe-Ni system, and its own dataset row is written Al0.75Co1Fe1Ni1.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -1.39775 | 1 |
| original | different | -6.27275 | 1 |
| cpt | same | -0.03410 | 1 |
| cpt | different | -8.28410 | 1 |

**original open-mask top 5:** ' same' (0.247), ' total' (0.062), ' average' (0.043), ' resulting' (0.033), ' corresponding' (0.033)
**cpt open-mask top 5:** ' same' (0.966), ' correct' (0.004), ' equivalent' (0.003), ' corresponding' (0.003), ' exact' (0.002)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-eutectic-ehea — Alloy equivalence

As atomic-ratio formulas, the eutectic alloy AlCoCrFeNi2.1 and AlCoCrFeNi have {answer} normalized elemental compositions.

Expected: different

The trailing 2.1 changes the nickel share; the reported eutectic composition AlCoCrFeNi2.1 is deliberately different from the equiatomic spelling AlCoCrFeNi.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -1.60433 | 1 |
| original | same | -4.91683 | 1 |
| cpt | different | -0.77672 | 1 |
| cpt | same | -5.65172 | 1 |

**original open-mask top 5:** ' different' (0.201), ' similar' (0.167), ' the' (0.147), ' identical' (0.061), ' their' (0.054)
**cpt open-mask top 5:** ' different' (0.460), ' identical' (0.217), ' similar' (0.080), ' their' (0.038), ' the' (0.033)

Deterministic composition reference: False
Equal atomic ratios do not establish equal microstructure or properties.

## alloy-at-percent-scale — Alloy equivalence

Interpreting the numerals as atomic percentages, Al20Co20Cr20Fe20Ni20 in at.% and the atomic-fraction formula Al0.2Co0.2Cr0.2Fe0.2Ni0.2 describe the {answer} normalized elemental composition.

Expected: same

20 at.% of each element is an atomic fraction of 0.2; only the scale of the numerals differs. Equiatomic AlCoCrFeNi is a real five-component HEA.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -3.20460 | 1 |
| original | different | -7.14210 | 1 |
| cpt | same | -0.30035 | 1 |
| cpt | different | -6.92535 | 1 |

**original open-mask top 5:** ' following' (0.249), ' total' (0.117), ' resulting' (0.063), ' above' (0.059), ' same' (0.041)
**cpt open-mask top 5:** ' same' (0.741), ' following' (0.035), ' corresponding' (0.014), ' correct' (0.012), ' approximate' (0.008)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## notation-alias-cantor — Alloy notation

The alloy name 'Cantor alloy' in one paper and the formula CoCrFeMnNi in another paper refer to the {answer} nominal alloy composition.

Expected: same

'Cantor alloy' is the widely used name for equiatomic CoCrFeMnNi. Alias names cannot be parsed by the ratio checker, so this row is hand-annotated.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.01620 | 1 |
| original | different | -7.70370 | 1 |
| cpt | same | -0.04971 | 1 |
| cpt | different | -5.36221 | 1 |

**original open-mask top 5:** ' same' (0.984), ' following' (0.002), ' identical' (0.002), ' above' (0.001), ' corresponding' (0.001)
**cpt open-mask top 5:** ' same' (0.952), ' following' (0.011), ' actual' (0.006), ' different' (0.005), ' identical' (0.002)

## notation-hyphen-list — Alloy notation

A paper writes an alloy as the hyphen-separated element list Co-Cr-Fe-Mn-Ni, and another paper writes the compact formula CoCrFeMnNi. These denote the {answer} nominal alloy composition.

Expected: same

Hyphen-separated element symbols give the same composition as the compact formula. Hand-annotated; the parser accepts no separators.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.04710 | 1 |
| original | different | -6.98460 | 1 |
| cpt | same | -0.00728 | 1 |
| cpt | different | -9.19478 | 1 |

**original open-mask top 5:** ' same' (0.954), ' corresponding' (0.004), ' exact' (0.003), ' equivalent' (0.002), ' identical' (0.002)
**cpt open-mask top 5:** ' same' (0.993), ' identical' (0.001), ' exact' (0.001), ' correct' (0.001), ' actual' (0.000)

## notation-hec-expanded — Alloy notation

For high-entropy carbide notation, the group formula (Hf0.2Zr0.2Ta0.2Nb0.2Ti0.2)C and the expanded formula Hf0.2Zr0.2Ta0.2Nb0.2Ti0.2C1 have the {answer} normalized elemental composition.

Expected: same

The group notation lists one fifth of each metal before one carbon; expanding the group and dividing by the total gives the same composition. (Hf,Zr,Ta,Nb,Ti)C carbides are reported in the HEC literature.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.01305 | 1 |
| original | different | -8.76305 | 1 |
| cpt | same | -0.00460 | 1 |
| cpt | different | -10.50460 | 1 |

**original open-mask top 5:** ' same' (0.987), ' following' (0.004), ' identical' (0.001), ' correct' (0.001), ' corresponding' (0.001)
**cpt open-mask top 5:** ' same' (0.995), ' identical' (0.001), ' correct' (0.001), ' equivalent' (0.000), ' following' (0.000)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## notation-hec-substoichiometric — Alloy notation

As group formulas, (Nb0.2Ta0.2Ti0.2W0.2Zr0.2)C and the carbon-deficient (Nb0.2Ta0.2Ti0.2W0.2Zr0.2)C0.5 have {answer} normalized elemental compositions.

Expected: different

With the metal group identical, halving the carbon coefficient halves the carbon share, so the normalized compositions differ. The (Nb,Ta,Ti,W,Zr)C system is studied with non-stoichiometric carbon in real HEC experiments.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -3.28261 | 1 |
| original | same | -4.72011 | 1 |
| cpt | different | -1.68206 | 1 |
| cpt | same | -5.18206 | 1 |

**original open-mask top 5:** ' the' (0.230), ' similar' (0.116), ' their' (0.109), ' identical' (0.066), ' been' (0.062)
**cpt open-mask top 5:** ' identical' (0.347), ' different' (0.186), ' similar' (0.145), ' the' (0.037), ' their' (0.025)

Deterministic composition reference: False
Equal atomic ratios do not establish equal microstructure or properties.

## notation-hec-metal-ratio — Alloy notation

As group formulas, the reported carbide (Hf0.25Ta0.25Zr0.25Ti0.25)C and the reported carbide (Hf0.25Ta0.25Zr0.25Nb0.25)C have {answer} normalized elemental compositions.

Expected: different

(Hf-Ta-Zr-Ti)C and (Hf-Ta-Zr-Nb)C are both reported high-entropy carbides; swapping Ti for Nb inside the group changes the composition even though the outer notations look alike.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -1.48773 | 1 |
| original | same | -4.23773 | 1 |
| cpt | different | -1.63001 | 1 |
| cpt | same | -5.06751 | 1 |

**original open-mask top 5:** ' different' (0.226), ' the' (0.176), ' identical' (0.094), ' similar' (0.088), ' their' (0.069)
**cpt open-mask top 5:** ' identical' (0.323), ' different' (0.196), ' the' (0.105), ' similar' (0.064), ' their' (0.064)

Deterministic composition reference: False
Equal atomic ratios do not establish equal microstructure or properties.

## notation-group-expansion — Alloy notation

Expanding the group, the notation (Mg0.2Co0.2Ni0.2Cu0.2Zn0.2)O and the flat formula Mg0.2Co0.2Ni0.2Cu0.2Zn0.2O1 have the {answer} normalized elemental composition.

Expected: same

A parenthesized group distributes its outer coefficient over every inner coefficient, so the group notation and the flat expansion denote the same composition. (Mg0.2Co0.2Ni0.2Cu0.2Zn0.2)O is the first reported entropy-stabilized oxide (Rost et al., Nat. Commun. 6:8485, 2015).

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.05022 | 1 |
| original | different | -8.80022 | 1 |
| cpt | same | -0.02423 | 1 |
| cpt | different | -9.89923 | 1 |

**original open-mask top 5:** ' same' (0.951), ' following' (0.025), ' correct' (0.005), ' identical' (0.001), ' given' (0.001)
**cpt open-mask top 5:** ' same' (0.976), ' correct' (0.005), ' highest' (0.003), ' best' (0.002), ' identical' (0.001)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## notation-invar-convert — Alloy notation

One paper lists an Invar specimen as Fe64Ni36 in atomic percent and another lists the same specimen as Fe62.8Ni37.2 in weight percent. These two percentage lists describe the {answer} alloy composition.

Expected: same

Converting Fe64Ni36 at.% with M(Fe) = 55.845 g/mol and M(Ni) = 58.693 g/mol gives about 62.8 wt.% Fe and 37.2 wt.% Ni. Invar is the classic Fe-Ni alloy near this composition. Hand-annotated; the checker does not convert bases.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.05977 | 1 |
| original | different | -5.12227 | 1 |
| cpt | same | -0.04552 | 1 |
| cpt | different | -6.23302 | 1 |

**original open-mask top 5:** ' same' (0.942), ' exact' (0.009), ' identical' (0.006), ' different' (0.006), ' correct' (0.002)
**cpt open-mask top 5:** ' same' (0.955), ' identical' (0.011), ' exact' (0.006), ' actual' (0.005), ' correct' (0.003)

## notation-invar-rounded — Alloy notation

An Invar specimen listed as Fe64Ni36 at.% and the same specimen listed as about Fe63Ni37 wt.% have the {answer} elemental composition.

Expected: same

Fe64Ni36 at.% converts to about 62.85/37.15 wt.%, which rounds to Fe63Ni37 wt.% at two significant figures; quoted compositions are routinely rounded. Hand-annotated.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.01245 | 1 |
| original | different | -8.07495 | 1 |
| cpt | same | -0.01130 | 1 |
| cpt | different | -9.07380 | 1 |

**original open-mask top 5:** ' same' (0.988), ' identical' (0.007), ' correct' (0.001), ' similar' (0.001), ' following' (0.001)
**cpt open-mask top 5:** ' same' (0.989), ' identical' (0.007), ' correct' (0.001), ' exact' (0.001), ' opposite' (0.001)

## notation-basis-mismatch — Alloy notation

An alloy described as Fe64Ni36 in atomic percent and an alloy described as Fe64Ni36 in weight percent have {answer} normalized elemental compositions.

Expected: different

64 and 36 read as weight percent convert to about 65.1 and 34.9 at.% because the atomic masses differ, so the same numerals on different bases denote different compositions. Hand-annotated.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -0.80594 | 1 |
| original | same | -4.99344 | 1 |
| cpt | different | -0.83341 | 1 |
| cpt | same | -5.08341 | 1 |

**original open-mask top 5:** ' different' (0.447), ' identical' (0.128), ' similar' (0.113), ' the' (0.078), ' been' (0.053)
**cpt open-mask top 5:** ' different' (0.435), ' identical' (0.384), ' the' (0.036), ' equivalent' (0.028), ' similar' (0.028)

## notation-ti64-basis — Alloy notation

In the alloy Ti-6Al-4V the numerals 6 and 4 are aluminium and vanadium in weight percent. A description with 6 and 4 as aluminium and vanadium in atomic percent defines {answer} alloy composition from Ti-6Al-4V.

Expected: different

Ti-6Al-4V uses weight percent: 6 wt.% Al and 4 wt.% V correspond to about 10.2 and 3.6 at.% on a roughly 86.2 at.% Ti balance, not 6 and 4 at.%. Hand-annotated; hyphenated designations and bases are outside the parser.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -6.91935 | 1 |
| original | same | -9.79435 | 1 |
| cpt | different | -2.77464 | 1 |
| cpt | same | -8.71214 | 1 |

**original open-mask top 5:** ' the' (0.844), ' an' (0.069), ' this' (0.048), ' its' (0.014), ' their' (0.006)
**cpt open-mask top 5:** ' the' (0.760), ' an' (0.103), ' different' (0.062), ' another' (0.029), ' this' (0.014)

## science-ideal-gas-product — Scientific reasoning (non-materials)

For a fixed amount of an ideal gas, the state with pressure 2P and volume V and the state with pressure P and volume 2V have the {answer} pressure-volume product.

Expected: same

Both products equal 2PV. Elementary gas-law reasoning placed outside materials science; a paired control for scientific reading without alloy vocabulary.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.01504 | 1 |
| original | different | -8.76504 | 1 |
| cpt | same | -0.00463 | 1 |
| cpt | different | -10.87963 | 1 |

**original open-mask top 5:** ' same' (0.985), ' identical' (0.002), ' opposite' (0.001), ' equal' (0.001), ' corresponding' (0.001)
**cpt open-mask top 5:** ' same' (0.995), ' identical' (0.001), ' correct' (0.000), ' given' (0.000), ' equal' (0.000)

## science-ideal-gas-energy — Scientific reasoning (non-materials)

For a fixed amount of monatomic ideal gas heated by 10 kelvin, the constant-volume path and the constant-pressure path give the {answer} internal energy change.

Expected: same

U = (3/2) n R T depends only on temperature, so equal temperature rises give equal internal energy changes; the heat supplied differs because constant-pressure heating also does expansion work.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.37199 | 1 |
| original | different | -7.80949 | 1 |
| cpt | same | -0.02750 | 1 |
| cpt | different | -8.27750 | 1 |

**original open-mask top 5:** ' same' (0.689), ' total' (0.025), ' corresponding' (0.021), ' average' (0.020), ' net' (0.014)
**cpt open-mask top 5:** ' same' (0.973), ' total' (0.005), ' maximum' (0.004), ' net' (0.002), ' corresponding' (0.001)

## science-isotope-control — Scientific reasoning (non-materials)

One mole of ordinary water H2O and one mole of heavy water D2O have {answer} molar masses.

Expected: different

Negative control: D2O weighs about one gram more per mole than H2O because deuterium is roughly twice as heavy as hydrogen. Chemistry outside alloy-composition reasoning.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -2.15263 | 1 |
| original | same | -4.21513 | 1 |
| cpt | different | -0.36956 | 1 |
| cpt | same | -5.36956 | 1 |

**original open-mask top 5:** ' equal' (0.406), ' opposite' (0.132), ' different' (0.116), ' similar' (0.055), ' identical' (0.048)
**cpt open-mask top 5:** ' different' (0.691), ' equal' (0.120), ' identical' (0.083), ' similar' (0.044), ' opposite' (0.008)

## hea-principal-element-count — HEA knowledge

Under the most common definition, a high-entropy alloy contains at least {answer} principal elements.

Expected: five

The conventional rule is five or more principal elements (some authors accept four). Definition recall, not a property prediction.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | two | -1.77619 | 1 |
| original | five | -2.90119 | 1 |
| original | seven | -3.71369 | 1 |
| original | twenty | -5.46369 | 1 |
| cpt | two | -1.05582 | 1 |
| cpt | five | -3.05582 | 1 |
| cpt | seven | -4.18082 | 1 |
| cpt | twenty | -6.30582 | 1 |

**original open-mask top 5:** ' three' (0.192), ' two' (0.169), ' four' (0.132), ' six' (0.091), ' five' (0.055)
**cpt open-mask top 5:** ' two' (0.348), ' three' (0.186), ' four' (0.100), ' five' (0.047), ' six' (0.037)

## hea-entropy-ln-five — HEA knowledge

For an ideal equiatomic alloy with five components, the molar configurational entropy is about {answer} times the gas constant R.

Expected: 1.6

S = R ln 5 = 1.61 R. The reported idea-mixing value behind the common HEA convention.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 2.5 | -1.31052 | 3 |
| original | 1.6 | -1.60219 | 3 |
| original | 0.8 | -1.81052 | 3 |
| original | 5.0 | -2.87302 | 3 |
| cpt | 2.5 | -1.43291 | 3 |
| cpt | 1.6 | -1.51625 | 3 |
| cpt | 0.8 | -1.55791 | 3 |
| cpt | 5.0 | -2.97458 | 3 |

**original open-mask top 5:** ' three' (0.088), ' 10' (0.064), ' 5' (0.064), ' two' (0.064), ' five' (0.060)
**cpt open-mask top 5:** ' three' (0.094), ' five' (0.064), ' two' (0.064), ' four' (0.057), ' 10' (0.044)

## hea-cantor-fcc — HEA knowledge

At room temperature the conventional Cantor alloy CoCrFeMnNi is reported to form a predominantly {answer} solid-solution structure.

Expected: FCC

Canonical experimental result for equiatomic CoCrFeMnNi as reported in the founding Cantor et al. 2004 work. Known material fact, not a prediction for an arbitrary alloy.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | FCC | -8.42719 | 1 |
| original | BCC | -9.13072 | 2 |
| cpt | FCC | -6.36992 | 1 |
| cpt | BCC | -6.90737 | 2 |

**original open-mask top 5:** ' cubic' (0.576), ' amorphous' (0.047), ' metallic' (0.022), ' crystalline' (0.021), ' planar' (0.021)
**cpt open-mask top 5:** ' cubic' (0.347), ' amorphous' (0.128), ' crystalline' (0.068), ' metallic' (0.041), ' disordered' (0.022)

## hea-refractory-bcc — HEA knowledge

The refractory alloys MoNbTaW and MoNbTaVW are reported to form predominantly {answer} solid-solution structures at room temperature.

Expected: BCC

Canonical Senkov-type refractory HEA behaviour. Kept as a paired control so neither phase abbreviation is always favored.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | FCC | -8.94368 | 1 |
| original | BCC | -9.75017 | 2 |
| cpt | BCC | -7.37721 | 2 |
| cpt | FCC | -7.66510 | 1 |

**original open-mask top 5:** ' in' (0.173), ' amorphous' (0.119), ' cubic' (0.105), ' crystalline' (0.053), ' as' (0.023)
**cpt open-mask top 5:** ' cubic' (0.214), ' amorphous' (0.089), ' crystalline' (0.089), ' in' (0.048), ' as' (0.035)

## hea-aluminium-bcc-trend — HEA knowledge

In the AlxCoCrFeNi family, increasing the aluminium fraction progressively shifts the reported microstructure from FCC toward {answer}.

Expected: BCC

Empirically established directional trend in the real AlxCoCrFeNi system; a trend statement, not a phase predictor for one specific sample.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | FCC | -1.21984 | 1 |
| original | BCC | -3.94687 | 2 |
| cpt | FCC | -2.68858 | 1 |
| cpt | BCC | -3.39145 | 2 |

**original open-mask top 5:** ' FCC' (0.295), ' ABC' (0.062), ' AFM' (0.017), ' Fe' (0.015), ' amorphous' (0.014)
**cpt open-mask top 5:** ' cubic' (0.345), ' amorphous' (0.082), ' FCC' (0.068), ' granular' (0.018), ' AF' (0.017)

## hea-interstitial-solutes — HEA knowledge

Carbon and oxygen in high-entropy alloys are conventionally classed as {answer} solute atoms rather than principal components.

Expected: interstitial

Small non-metal atoms occupy interstitial sites; interstitial-engineered HEAs are a recognized subfield.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | principal | -1.86491 | 1 |
| original | interstitial | -8.42741 | 1 |
| cpt | principal | -4.56255 | 1 |
| cpt | interstitial | -5.12505 | 1 |

**original open-mask top 5:** ' the' (0.255), ' principal' (0.155), ' individual' (0.029), ' primary' (0.027), ' constituent' (0.025)
**cpt open-mask top 5:** ' minor' (0.087), ' secondary' (0.082), ' major' (0.072), ' the' (0.068), ' main' (0.036)

## materials-sem — Materials terminology

Scanning electron microscopy is commonly abbreviated as {answer}.

Expected: SEM

Microscopy abbreviation control, matching the XRD probe.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | SEM | -0.07486 | 1 |
| original | STM | -4.07486 | 1 |
| original | SXRD | -5.51750 | 3 |
| cpt | SEM | -0.01225 | 1 |
| cpt | STM | -6.26225 | 1 |
| cpt | SXRD | -6.53993 | 3 |

**original open-mask top 5:** ' SEM' (0.928), ' STEM' (0.036), ' STM' (0.017), 'SEM' (0.012), ' microscopy' (0.001)
**cpt open-mask top 5:** ' SEM' (0.988), ' STEM' (0.007), ' TEM' (0.003), ' STM' (0.002), 'SEM' (0.000)

## materials-tem — Materials terminology

Transmission electron microscopy is commonly abbreviated as {answer}.

Expected: TEM

A third microscopy abbreviation control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | TEM | -0.67180 | 1 |
| original | STM | -3.67180 | 1 |
| original | TGA | -8.18061 | 2 |
| cpt | TEM | -0.00529 | 1 |
| cpt | STM | -6.50529 | 1 |
| cpt | TGA | -6.87702 | 2 |

**original open-mask top 5:** ' TEM' (0.511), ' STEM' (0.451), ' STM' (0.025), 'TEM' (0.005), ' SEM' (0.002)
**cpt open-mask top 5:** ' TEM' (0.995), ' STEM' (0.003), ' STM' (0.001), ' SEM' (0.000), ' TM' (0.000)

## materials-eds — Materials terminology

Energy-dispersive X-ray spectroscopy is commonly abbreviated as {answer}.

Expected: EDS

Chemistry-characterization abbreviation; WDS is a distinct spectroscopy mode, not the same abbreviation.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | EDS | -2.58149 | 2 |
| original | WDS | -8.70649 | 2 |
| original | STM | -10.49866 | 1 |
| cpt | EDS | -3.38707 | 2 |
| cpt | WDS | -8.76207 | 2 |
| cpt | STM | -11.31784 | 1 |

**original open-mask top 5:** ' ESR' (0.733), ' AES' (0.028), ' ED' (0.027), ' DES' (0.020), ' EMS' (0.018)
**cpt open-mask top 5:** ' ESR' (0.313), ' STEM' (0.115), ' AES' (0.070), ' EX' (0.066), ' ISIS' (0.040)

## materials-dsc — Materials terminology

Differential scanning calorimetry is commonly abbreviated as {answer}.

Expected: DSC

Thermal-analysis abbreviation control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | DSC | -0.25873 | 2 |
| original | DSX | -6.94623 | 2 |
| original | SAM | -15.94912 | 1 |
| cpt | DSC | -0.08078 | 2 |
| cpt | DSX | -7.48703 | 2 |
| cpt | SAM | -13.64324 | 1 |

**original open-mask top 5:** ' DNS' (0.453), ' DEC' (0.147), ' dc' (0.061), ' DSS' (0.054), ' DC' (0.048)
**cpt open-mask top 5:** ' DSS' (0.373), ' DEC' (0.121), ' SDS' (0.065), ' DC' (0.065), ' CSS' (0.039)

## materials-vickers-hv — Materials terminology

Vickers hardness is denoted by the symbol {answer}.

Expected: HV

HV is Vickers; HB and HRC denote Brinell and Rockwell C scales. Relevant because HEA papers report HV values.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | HV | -3.46464 | 1 |
| original | HRC | -5.56122 | 2 |
| original | HB | -6.21464 | 1 |
| cpt | HV | -1.78512 | 1 |
| cpt | HB | -5.22262 | 1 |
| cpt | HRC | -5.70708 | 2 |

**original open-mask top 5:** ' V' (0.432), ' H' (0.080), ' v' (0.043), ' HV' (0.031), ' K' (0.024)
**cpt open-mask top 5:** ' V' (0.277), ' HV' (0.168), ' H' (0.079), ' K' (0.027), ' W' (0.026)

## materials-bragg-angle — Materials terminology

For a fixed X-ray wavelength, increasing the lattice parameter shifts diffraction peaks toward {answer} diffraction angles.

Expected: lower

Bragg's law: larger d needs smaller theta at fixed wavelength; complementary to the XRD abbreviation probe.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | higher | -1.24080 | 1 |
| original | lower | -2.11580 | 1 |
| cpt | higher | -0.79967 | 1 |
| cpt | lower | -1.79967 | 1 |

**original open-mask top 5:** ' higher' (0.289), ' larger' (0.155), ' smaller' (0.137), ' lower' (0.121), ' shorter' (0.039)
**cpt open-mask top 5:** ' higher' (0.449), ' lower' (0.165), ' larger' (0.146), ' smaller' (0.114), ' greater' (0.033)

## materials-strain-rate — Materials reasoning

Two identical specimens of the same alloy tension-tested at different strain rates can show different measured strengths. This statement is {answer}.

Expected: true

Rate sensitivity is routinely observed; 'can show' keeps the claim weak and true.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -0.93602 | 1 |
| original | true | -2.18602 | 1 |
| cpt | true | -2.85600 | 1 |
| cpt | false | -3.10600 | 1 |

**original open-mask top 5:** ' false' (0.392), ' incorrect' (0.270), ' true' (0.112), ' correct' (0.032), ' erroneous' (0.022)
**cpt open-mask top 5:** ' incorrect' (0.201), ' correct' (0.138), ' true' (0.057), ' misleading' (0.048), ' false' (0.045)

## materials-grain-size — Materials reasoning

For many crystalline materials, finer grains give higher room-temperature yield strength. This statement is {answer}.

Expected: true

Grain-boundary (Hall-Petch-type) strengthening is a standard effect; 'many' avoids a universal claim.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.18114 | 1 |
| original | true | -1.55614 | 1 |
| cpt | false | -1.74268 | 1 |
| cpt | true | -1.86768 | 1 |

**original open-mask top 5:** ' false' (0.307), ' true' (0.211), ' incorrect' (0.186), ' negative' (0.060), ' accurate' (0.047)
**cpt open-mask top 5:** ' incorrect' (0.198), ' false' (0.175), ' correct' (0.154), ' true' (0.154), ' accurate' (0.027)

## materials-solute-strengthening — Materials reasoning

Adding substitutional solute atoms usually increases a metal's yield strength by impeding dislocation motion. This statement is {answer}.

Expected: true

Solid-solution strengthening is a standard mechanism; 'usually' avoids a universal claim.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.13024 | 1 |
| original | true | -1.63024 | 1 |
| cpt | false | -1.52392 | 1 |
| cpt | true | -1.89892 | 1 |

**original open-mask top 5:** ' false' (0.323), ' incorrect' (0.252), ' true' (0.196), ' correct' (0.050), ' negative' (0.034)
**cpt open-mask top 5:** ' false' (0.218), ' incorrect' (0.218), ' correct' (0.150), ' true' (0.150), ' wrong' (0.029)

## materials-temperature-softening — Materials reasoning

A compression specimen tested at 500 degrees Celsius is expected to show essentially the same yield strength as one tested at 25 degrees Celsius. This statement is {answer}.

Expected: false

Thermal softening generally reduces high-temperature strength; this contrasts with the isothermal unit-conversion probes. This is why test temperature must accompany every strength value.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.22690 | 1 |
| original | true | -2.35190 | 1 |
| cpt | false | -1.83803 | 1 |
| cpt | true | -1.96303 | 1 |

**original open-mask top 5:** ' incorrect' (0.332), ' false' (0.293), ' true' (0.095), ' correct' (0.074), ' erroneous' (0.045)
**cpt open-mask top 5:** ' correct' (0.232), ' incorrect' (0.204), ' false' (0.159), ' true' (0.140), ' accurate' (0.020)

## materials-property-independence — Materials reasoning

One measured mechanical property such as hardness is sufficient to determine a different property such as corrosion resistance. This statement is {answer}.

Expected: false

Distinct material properties require separate measurements; extends the hardness-not-strength control across property families.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.29954 | 1 |
| original | true | -2.54954 | 1 |
| cpt | false | -1.34567 | 1 |
| cpt | true | -3.22067 | 1 |

**original open-mask top 5:** ' incorrect' (0.309), ' false' (0.273), ' true' (0.078), ' correct' (0.069), ' erroneous' (0.037)
**cpt open-mask top 5:** ' incorrect' (0.334), ' false' (0.260), ' correct' (0.085), ' true' (0.040), ' erroneous' (0.029)

## units-two-gpa — Units and numerical controls

A stress of 2 GPa is equal to {answer} MPa.

Expected: 2000

SI prefix arithmetic, mirrored in the reverse-direction probe.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 0.002 | -3.12551 | 3 |
| original | 20 | -3.84451 | 1 |
| original | 200 | -4.90701 | 1 |
| original | 2000 | -7.09451 | 1 |
| cpt | 20 | -2.56271 | 1 |
| cpt | 200 | -2.68771 | 1 |
| cpt | 2000 | -3.68771 | 1 |
| cpt | 0.002 | -3.74288 | 3 |

**original open-mask top 5:** ' 2' (0.230), ' 1' (0.085), ' 4' (0.075), ' 3' (0.062), ' 10' (0.045)
**cpt open-mask top 5:** ' 2' (0.346), ' 20' (0.077), ' 200' (0.068), ' 100' (0.041), ' 10' (0.041)

## units-gram-force-gpa — Units and numerical controls

A stress of 1000 MPa is equal to {answer} GPa.

Expected: 1

Reverse-direction GPa/MPa control so a fixed one-way conversion habit fails.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 1000 | -1.15426 | 1 |
| original | 1 | -1.90426 | 1 |
| original | 10 | -2.84176 | 1 |
| original | 100 | -2.90426 | 1 |
| cpt | 1 | -0.80258 | 1 |
| cpt | 10 | -2.05258 | 1 |
| cpt | 1000 | -2.55258 | 1 |
| cpt | 100 | -2.67758 | 1 |

**original open-mask top 5:** ' 1000' (0.315), ' 1' (0.149), ' 10' (0.058), ' 100' (0.055), ' 2' (0.023)
**cpt open-mask top 5:** ' 1' (0.448), ' 10' (0.128), ' 1000' (0.078), ' 100' (0.069), ' 2' (0.020)

## units-100-degrees — Units and numerical controls

A temperature of 100 degrees Celsius is equal to {answer} kelvin.

Expected: 373.15

Kelvin/Celsius control evaluated away from the 0-degree point.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 100 | -1.25419 | 1 |
| original | 0 | -2.25419 | 1 |
| original | 273.15 | -3.48510 | 3 |
| original | 373.15 | -4.46427 | 3 |
| cpt | 273.15 | -2.39160 | 3 |
| cpt | 373.15 | -2.76660 | 3 |
| cpt | 0 | -4.10916 | 1 |
| cpt | 100 | -4.23416 | 1 |

**original open-mask top 5:** ' 100' (0.285), ' 1' (0.252), ' 0' (0.105), ' 101' (0.064), ' one' (0.034)
**cpt open-mask top 5:** ' 273' (0.330), ' 373' (0.227), ' 1' (0.094), ' 1000' (0.051), ' 300' (0.039)

## units-zero-kelvin — Units and numerical controls

A temperature of 0 kelvin is equal to {answer} degrees Celsius.

Expected: -273.15

Reverse-direction temperature control including the sign.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 0 | -0.14748 | 1 |
| original | 273.15 | -3.61597 | 3 |
| original | 100 | -3.89748 | 1 |
| original | -273.15 | -6.01505 | 4 |
| cpt | 0 | -0.07642 | 1 |
| cpt | 273.15 | -1.73684 | 3 |
| cpt | -273.15 | -5.11266 | 4 |
| cpt | 100 | -5.32642 | 1 |

**original open-mask top 5:** ' 0' (0.863), ' zero' (0.033), ' 100' (0.020), ' 273' (0.010), ' 10' (0.007)
**cpt open-mask top 5:** ' 0' (0.926), ' zero' (0.041), ' 32' (0.006), ' 100' (0.005), ' 273' (0.004)

## units-fraction-04 — Units and numerical controls

An atomic fraction of 0.4 is equal to {answer} atomic percent.

Expected: 40

Fraction-to-percent direction; supports reading at.% statements like the Invar and Ti-6Al-4V notation probes.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 4 | -1.07589 | 1 |
| original | 40 | -4.88839 | 1 |
| original | 400 | -5.57589 | 1 |
| original | 19 | -8.01339 | 1 |
| cpt | 4 | -1.31337 | 1 |
| cpt | 40 | -1.93837 | 1 |
| cpt | 400 | -4.00087 | 1 |
| cpt | 19 | -7.37587 | 1 |

**original open-mask top 5:** ' 4' (0.341), ' one' (0.161), ' 1' (0.161), ' four' (0.059), ' an' (0.041)
**cpt open-mask top 5:** ' 4' (0.269), ' 40' (0.144), ' four' (0.144), ' 24' (0.025), ' 20' (0.025)

## units-fraction-03 — Units and numerical controls

An atomic percent of 30 is equal to the fraction {answer}.

Expected: 0.3

Percent-to-fraction direction; ties the unit layer to the atomic-fraction formulas used by the ratio checker.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 30 | -2.04769 | 1 |
| original | 3 | -4.23519 | 1 |
| original | 29 | -4.79769 | 1 |
| original | 0.3 | -6.42499 | 3 |
| cpt | 30 | -1.69406 | 1 |
| cpt | 0.3 | -2.86954 | 3 |
| cpt | 3 | -2.94406 | 1 |
| cpt | 29 | -5.00656 | 1 |

**original open-mask top 5:** ' 30' (0.129), ' percent' (0.069), ' 100' (0.051), ' 10' (0.029), ' 1' (0.027)
**cpt open-mask top 5:** ' 30' (0.184), ' 100' (0.053), ' 3' (0.053), ' 1' (0.036), ' 2' (0.032)

## units-percent-sum — Units and numerical controls

The atomic percentages of all components of an alloy must add up to {answer} percent.

Expected: 100

Composition closure check, relevant when reading dataset rows or percent statements in papers.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 100 | -0.98200 | 1 |
| original | 20 | -3.35700 | 1 |
| original | 90 | -3.98200 | 1 |
| original | 150 | -5.04450 | 1 |
| cpt | 100 | -0.38768 | 1 |
| cpt | 20 | -4.32518 | 1 |
| cpt | 90 | -4.38768 | 1 |
| cpt | 150 | -5.95018 | 1 |

**original open-mask top 5:** ' 100' (0.375), ' 10' (0.051), ' 20' (0.035), ' 50' (0.031), ' one' (0.027)
**cpt open-mask top 5:** ' 100' (0.679), ' 50' (0.063), ' 20' (0.013), ' 90' (0.012), ' one' (0.010)

## units-megapascal-force-area — Units and numerical controls

In SI units, 1 MPa is equal to {answer} newton per square millimetre.

Expected: 1

Pressure-unit identity used in every strength table.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | 1 | -0.33409 | 1 |
| original | 1000 | -6.20909 | 1 |
| original | 100 | -6.58409 | 1 |
| original | 10 | -6.83409 | 1 |
| cpt | 1 | -0.87760 | 1 |
| cpt | 1000 | -3.25260 | 1 |
| cpt | 100 | -5.25260 | 1 |
| cpt | 10 | -5.62760 | 1 |

**original open-mask top 5:** ' 1' (0.716), ' one' (0.263), ' a' (0.008), ' 1000' (0.002), ' 100' (0.001)
**cpt open-mask top 5:** ' one' (0.471), ' 1' (0.416), ' 1000' (0.039), ' 106' (0.014), ' a' (0.014)

## general-strength-comparative — General English

Two alloy samples have tensile strengths of 800 MPa and 1200 MPa. The sample with 1200 MPa is {answer}.

Expected: stronger

Comparative-adjective probe built on plain numbers; combines language with an arithmetic-free comparison.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | stronger | -5.74919 | 1 |
| original | softer | -7.18669 | 1 |
| cpt | stronger | -2.68956 | 1 |
| cpt | softer | -6.62706 | 1 |

**original open-mask top 5:** ' used' (0.120), ' shown' (0.053), ' tested' (0.032), ' selected' (0.027), ' thicker' (0.025)
**cpt open-mask top 5:** ' preferred' (0.135), ' selected' (0.093), ' used' (0.072), ' stronger' (0.068), ' tested' (0.039)

## general-hardness-superlative — General English

Three samples have hardness 200 HV, 300 HV and 700 HV. The sample with 700 HV is the {answer}.

Expected: hardest

Superlative-adjective probe with the largest value uniquely identified.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | hardest | -4.67146 | 1 |
| original | softest | -5.03698 | 2 |
| cpt | hardest | -1.25609 | 1 |
| cpt | softest | -2.84049 | 2 |

**original open-mask top 5:** ' best' (0.374), ' largest' (0.121), ' highest' (0.051), ' strongest' (0.045), ' oldest' (0.045)
**cpt open-mask top 5:** ' hardest' (0.285), ' best' (0.251), ' strongest' (0.077), ' largest' (0.056), ' finest' (0.030)

## general-above-higher — General English

A temperature described as above 300 kelvin is {answer} than 300 kelvin.

Expected: higher

Spatial preposition control; complements the antonym and word-order probes.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | higher | -1.92589 | 1 |
| original | lower | -4.42589 | 1 |
| cpt | higher | -1.93706 | 1 |
| cpt | lower | -4.31206 | 1 |

**original open-mask top 5:** ' greater' (0.576), ' higher' (0.146), ' more' (0.114), ' less' (0.069), ' warmer' (0.047)
**cpt open-mask top 5:** ' greater' (0.646), ' higher' (0.144), ' less' (0.077), ' more' (0.053), ' warmer' (0.041)

## science-boyle-law — Scientific reasoning (non-materials)

For a fixed amount of ideal gas at constant temperature, doubling the pressure halves the volume. This statement is {answer}.

Expected: true

Boyle's-law control; pairs with the pressure-volume product probe.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | true | -0.72610 | 1 |
| original | false | -1.22610 | 1 |
| cpt | false | -0.68916 | 1 |
| cpt | true | -1.18916 | 1 |

**original open-mask top 5:** ' true' (0.484), ' false' (0.293), ' incorrect' (0.108), ' negative' (0.031), ' correct' (0.027)
**cpt open-mask top 5:** ' false' (0.502), ' true' (0.304), ' correct' (0.068), ' incorrect' (0.060), ' wrong' (0.010)

## science-net-force — Scientific reasoning (non-materials)

A cart is pulled left with 5 newtons and pulled right with 5 newtons at the same time, so its net horizontal force is {answer} newtons.

Expected: zero

Balanced-force reasoning outside materials science.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | five | -6.64265 | 1 |
| original | ten | -7.45515 | 1 |
| original | zero | -8.08015 | 1 |
| original | one | -10.83015 | 1 |
| cpt | ten | -8.42085 | 1 |
| cpt | zero | -8.48335 | 1 |
| cpt | five | -9.29585 | 1 |
| cpt | one | -13.13960 | 1 |

**original open-mask top 5:** ' 5' (0.219), ' 10' (0.151), ' 6' (0.081), ' 7' (0.055), ' 15' (0.041)
**cpt open-mask top 5:** ' 10' (0.424), ' 15' (0.121), ' 5' (0.095), ' 20' (0.083), ' 25' (0.039)

## science-heated-density — Scientific reasoning (non-materials)

At constant pressure, heating a fixed amount of ideal gas makes it {answer} dense.

Expected: less

Ideal-gas density control; directional-phrase probe like the Bragg-angle items.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | less | -0.66330 | 1 |
| original | more | -1.16330 | 1 |
| cpt | less | -0.58198 | 1 |
| cpt | more | -0.83198 | 1 |

**original open-mask top 5:** ' less' (0.515), ' more' (0.312), ' very' (0.037), ' infinitely' (0.033), ' optically' (0.008)
**cpt open-mask top 5:** ' less' (0.559), ' more' (0.435), ' increasingly' (0.001), ' become' (0.001), ' very' (0.000)

## science-condensation — Scientific reasoning (non-materials)

For most substances, cooling a gas at constant pressure below its boiling temperature turns it into a {answer}.

Expected: liquid

Condensation control; 'for most substances' keeps the statement true (a minority of substances subliminate in accessible conditions).

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | liquid | -0.18553 | 1 |
| original | solid | -3.18553 | 1 |
| cpt | liquid | -0.08054 | 1 |
| cpt | solid | -2.58054 | 1 |

**original open-mask top 5:** ' liquid' (0.831), ' vapor' (0.053), ' gas' (0.047), ' solid' (0.041), ' fluid' (0.004)
**cpt open-mask top 5:** ' liquid' (0.923), ' solid' (0.076), ' vapor' (0.001), ' fluid' (0.000), ' metal' (0.000)

## science-heat-flow-direction — Scientific reasoning (non-materials)

Heat flows spontaneously from a hotter body to a {answer} body.

Expected: colder

Everyday thermodynamics matching the internal-energy probe; no alloy vocabulary.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | colder | -0.79838 | 2 |
| original | hotter | -2.42338 | 2 |
| cpt | colder | -0.10211 | 2 |
| cpt | hotter | -5.16461 | 2 |

**original open-mask top 5:** ' cooler' (0.927), ' warmer' (0.028), ' cold' (0.022), ' cool' (0.007), ' thinner' (0.003)
**cpt open-mask top 5:** ' cooler' (0.993), ' cold' (0.002), ' warmer' (0.002), ' cool' (0.001), ' cooled' (0.001)

## science-newton-definition — Scientific reasoning (non-materials)

In SI units, one newton is the force that accelerates a one-kilogram mass at {answer} metre per square second.

Expected: one

Force-unit definition; a non-materials control for numerical staleness probes.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | one | -0.07931 | 1 |
| original | ten | -7.89181 | 1 |
| original | zero | -8.07931 | 1 |
| cpt | one | -0.01054 | 1 |
| cpt | ten | -11.13554 | 1 |
| cpt | zero | -13.76054 | 1 |

**original open-mask top 5:** ' one' (0.924), ' 1' (0.052), ' a' (0.015), ' 100' (0.000), ' per' (0.000)
**cpt open-mask top 5:** ' one' (0.990), ' 1' (0.010), ' a' (0.000), ' ONE' (0.000), ' 10' (0.000)

## science-archimedes — Scientific reasoning (non-materials)

An ice cube floating in a glass of water displaces a weight of water {answer} to the weight of the ice cube.

Expected: equal

Archimedes' principle for floating bodies; qualitative physics control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | equal | -0.08958 | 1 |
| original | double | -10.15208 | 1 |
| cpt | equal | -0.03891 | 1 |
| cpt | double | -14.28891 | 1 |

**original open-mask top 5:** ' equal' (0.914), ' proportional' (0.035), ' equivalent' (0.028), ' corresponding' (0.004), ' similar' (0.003)
**cpt open-mask top 5:** ' equal' (0.962), ' equivalent' (0.020), ' proportional' (0.008), ' corresponding' (0.004), ' due' (0.001)
