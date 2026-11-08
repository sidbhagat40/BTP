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
| cpt | nickel | -0.00237 | 1 |
| cpt | aluminum | -7.50237 | 1 |
| cpt | copper | -9.37737 | 1 |
| cpt | titanium | -10.87737 | 1 |

**original open-mask top 5:** ' nickel' (0.969), ' zinc' (0.007), ' copper' (0.005), ' silicon' (0.005), ' Ni' (0.003)
**cpt open-mask top 5:** ' nickel' (0.998), ' nitrogen' (0.001), ' aluminum' (0.001), ' Ni' (0.000), ' zinc' (0.000)

## hea-entropy-equiatomic — HEA knowledge

For a fixed number of components under the ideal random-mixing model, configurational entropy is maximized at {answer} atomic fractions.

Expected: equal

For ideal configurational entropy -R sum(x_i ln x_i), equal fractions maximize entropy for a fixed component count.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | equal | -4.07392 | 1 |
| original | unequal | -6.76142 | 1 |
| cpt | equal | -1.27246 | 1 |
| cpt | unequal | -5.70996 | 1 |

**original open-mask top 5:** ' all' (0.111), ' fixed' (0.111), ' low' (0.081), ' constant' (0.067), ' high' (0.063)
**cpt open-mask top 5:** ' equal' (0.280), ' lower' (0.071), ' low' (0.071), ' high' (0.055), ' all' (0.038)

## hea-no-single-phase-guarantee — HEA knowledge

A high configurational entropy alone guarantees a single-phase solid solution in every high-entropy alloy. This statement is {answer}.

Expected: false

Enthalpy, temperature, kinetics and ordering also influence phase stability. HEA is not a guarantee of one phase.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -0.84520 | 1 |
| original | true | -2.09520 | 1 |
| cpt | false | -1.15079 | 1 |
| cpt | true | -3.58829 | 1 |

**original open-mask top 5:** ' false' (0.429), ' incorrect' (0.230), ' true' (0.123), ' negative' (0.045), ' wrong' (0.040)
**cpt open-mask top 5:** ' false' (0.316), ' incorrect' (0.103), ' invalid' (0.080), ' erroneous' (0.059), ' unreasonable' (0.046)

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
| cpt | tungsten | -2.71648 | 2 |
| cpt | vanadium | -4.46648 | 2 |
| cpt | titanium | -5.75842 | 1 |
| cpt | tin | -9.25842 | 1 |

**original open-mask top 5:** ' water' (0.114), ' gold' (0.045), ' metal' (0.045), ' potassium' (0.031), ' quartz' (0.029)
**cpt open-mask top 5:** ' oxygen' (0.152), ' W' (0.105), ' metal' (0.060), ' Ta' (0.044), ' Mo' (0.041)

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
| cpt | 5 | -2.35927 | 1 |
| cpt | 20 | -4.23427 | 1 |
| cpt | 25 | -4.54677 | 1 |
| cpt | 50 | -5.73427 | 1 |

**original open-mask top 5:** ' equal' (0.314), ' one' (0.090), ' the' (0.062), ' 100' (0.033), ' zero' (0.031)
**cpt open-mask top 5:** ' equal' (0.616), ' 5' (0.094), ' five' (0.065), ' one' (0.051), ' 10' (0.024)

## alloy-order — Alloy equivalence

Assuming omitted coefficients are one and all coefficients denote atomic ratios, CoCrFeMnNi and NiMnFeCrCo have the {answer} normalized elemental composition.

Expected: same

Element order in a simple formula does not change its normalized composition. This does not establish equal processing or properties.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.00567 | 1 |
| original | different | -10.25567 | 1 |
| cpt | same | -0.02046 | 1 |
| cpt | different | -10.27046 | 1 |

**original open-mask top 5:** ' same' (0.994), ' identical' (0.001), ' following' (0.001), ' correct' (0.001), ' corresponding' (0.000)
**cpt open-mask top 5:** ' same' (0.980), ' identical' (0.007), ' similar' (0.002), ' highest' (0.001), ' equivalent' (0.001)

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
| cpt | same | -0.14530 | 1 |
| cpt | different | -7.58280 | 1 |

**original open-mask top 5:** ' same' (0.981), ' following' (0.006), ' identical' (0.003), ' correct' (0.001), ' corresponding' (0.001)
**cpt open-mask top 5:** ' same' (0.865), ' highest' (0.030), ' similar' (0.030), ' most' (0.008), ' lowest' (0.008)

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
| cpt | same | -2.96996 | 1 |
| cpt | different | -7.03246 | 1 |

**original open-mask top 5:** ' same' (0.338), ' total' (0.049), ' average' (0.036), ' corresponding' (0.036), ' following' (0.030)
**cpt open-mask top 5:** ' ideal' (0.096), ' best' (0.066), ' same' (0.051), ' optimal' (0.048), ' average' (0.048)

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
| cpt | different | -3.01597 | 1 |
| cpt | same | -5.76597 | 1 |

**original open-mask top 5:** ' the' (0.210), ' similar' (0.135), ' their' (0.119), ' different' (0.093), ' identical' (0.028)
**cpt open-mask top 5:** ' similar' (0.385), ' the' (0.182), ' different' (0.049), ' identical' (0.038), ' their' (0.032)

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
| cpt | different | -3.23356 | 1 |
| cpt | same | -6.04606 | 1 |

**original open-mask top 5:** ' different' (0.421), ' similar' (0.121), ' the' (0.100), ' their' (0.037), ' identical' (0.030)
**cpt open-mask top 5:** ' similar' (0.699), ' the' (0.051), ' different' (0.039), ' higher' (0.031), ' comparable' (0.029)

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
| cpt | different | -3.87123 | 1 |
| cpt | same | -5.87123 | 1 |

**original open-mask top 5:** ' different' (0.337), ' similar' (0.180), ' identical' (0.124), ' the' (0.071), ' their' (0.028)
**cpt open-mask top 5:** ' similar' (0.609), ' the' (0.106), ' identical' (0.050), ' comparable' (0.037), ' different' (0.021)

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
| cpt | same | -0.01725 | 1 |
| cpt | different | -10.01725 | 1 |

**original open-mask top 5:** ' same' (0.996), ' identical' (0.001), ' following' (0.000), ' equivalent' (0.000), ' similar' (0.000)
**cpt open-mask top 5:** ' same' (0.983), ' identical' (0.005), ' similar' (0.003), ' highest' (0.002), ' equivalent' (0.001)

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
| cpt | false | -1.36291 | 1 |
| cpt | true | -1.48791 | 1 |

**original open-mask top 5:** ' incorrect' (0.382), ' false' (0.298), ' true' (0.124), ' correct' (0.066), ' negative' (0.019)
**cpt open-mask top 5:** ' false' (0.256), ' true' (0.226), ' invalid' (0.073), ' incorrect' (0.057), ' impossible' (0.029)

## alloy-missing-information — Materials reasoning

An alloy's nominal formula is supplied without processing history, temperature, or loading conditions. Its exact yield strength is {answer} from that formula alone.

Expected: undetermined

A composition string is insufficient for a unique numerical yield-strength prediction.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | known | -2.53977 | 1 |
| original | undetermined | -7.45124 | 2 |
| cpt | known | -3.30985 | 1 |
| cpt | undetermined | -7.80117 | 2 |

**original open-mask top 5:** ' determined' (0.312), ' calculated' (0.189), ' derived' (0.147), ' obtained' (0.089), ' known' (0.079)
**cpt open-mask top 5:** ' derived' (0.224), ' determined' (0.174), ' obtained' (0.136), ' calculated' (0.120), ' deduced' (0.073)

## materials-fcc — Materials terminology

The standard abbreviation for a face-centered cubic crystal structure is {answer}.

Expected: FCC

Abbreviation recognition; not a prediction that a particular alloy must be FCC.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | FCC | -2.72746 | 1 |
| original | BCC | -4.77278 | 2 |
| original | HCP | -7.39778 | 2 |
| cpt | FCC | -0.63821 | 1 |
| cpt | BCC | -2.23040 | 2 |
| cpt | HCP | -3.98040 | 2 |

**original open-mask top 5:** ' FC' (0.259), ' CF' (0.122), ' C' (0.079), ' Cf' (0.074), ' FCC' (0.065)
**cpt open-mask top 5:** ' FCC' (0.528), ' used' (0.086), ' f' (0.030), ' a' (0.026), ' cubic' (0.019)

## materials-bcc — Materials terminology

The standard abbreviation for a body-centered cubic crystal structure is {answer}.

Expected: BCC

A matched terminology control to avoid favoring only one phase abbreviation.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | BCC | -1.79856 | 2 |
| original | FCC | -4.39351 | 1 |
| original | HCP | -7.48606 | 2 |
| cpt | BCC | -0.51206 | 2 |
| cpt | FCC | -1.78535 | 1 |
| cpt | HCP | -4.29331 | 2 |

**original open-mask top 5:** ' BC' (0.299), ' CB' (0.141), ' C' (0.076), ' CBC' (0.049), ' bc' (0.032)
**cpt open-mask top 5:** ' FCC' (0.168), ' b' (0.096), ' used' (0.054), ' B' (0.054), ' c' (0.033)

## materials-hcp — Materials terminology

The standard abbreviation for a hexagonal close-packed crystal structure is {answer}.

Expected: HCP

A third phase-name control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | HCP | -3.10759 | 2 |
| original | FCC | -4.72452 | 1 |
| original | BCC | -5.20134 | 2 |
| cpt | HCP | -0.25712 | 2 |
| cpt | FCC | -2.21798 | 1 |
| cpt | BCC | -4.60087 | 2 |

**original open-mask top 5:** ' hex' (0.244), ' Hex' (0.062), ' HP' (0.048), ' HH' (0.023), ' H' (0.021)
**cpt open-mask top 5:** ' FCC' (0.109), ' used' (0.090), ' hex' (0.066), ' H' (0.058), ' a' (0.029)

## materials-xrd — Materials terminology

X-ray diffraction is commonly abbreviated as {answer}.

Expected: XRD

SEM is scanning electron microscopy; DSC is differential scanning calorimetry.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | XRD | -0.15693 | 2 |
| original | SEM | -8.85066 | 1 |
| original | DSC | -9.03193 | 2 |
| cpt | XRD | -0.23232 | 2 |
| cpt | DSC | -5.57607 | 2 |
| cpt | SEM | -5.79448 | 1 |

**original open-mask top 5:** ' diffraction' (0.157), ' X' (0.090), ' ESR' (0.070), ' DX' (0.070), ' dx' (0.062)
**cpt open-mask top 5:** ' PDF' (0.177), ' ND' (0.061), ' ED' (0.057), ' DX' (0.051), ' Oxford' (0.031)

## materials-tensile-compression — Materials reasoning

A tensile test pulls a sample, whereas a compression test {answer} it.

Expected: compresses

Distinguishes loading mode rather than making an unsupported alloy-strength claim.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | compresses | -1.15312 | 2 |
| original | dissolves | -6.12187 | 2 |
| original | melts | -6.49687 | 2 |
| cpt | compresses | -1.56777 | 2 |
| cpt | melts | -4.91152 | 2 |
| cpt | dissolves | -6.59902 | 2 |

**original open-mask top 5:** ' pushes' (0.296), ' stretches' (0.058), ' breaks' (0.040), ' drops' (0.031), ' cuts' (0.029)
**cpt open-mask top 5:** ' pushes' (0.709), ' pins' (0.123), ' breaks' (0.035), ' strains' (0.017), ' drives' (0.010)

## materials-hardness-not-strength — Materials reasoning

Hardness and tensile strength are exactly the same physical measurement. This statement is {answer}.

Expected: false

They can correlate within material classes but are different measurements.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.05152 | 1 |
| original | true | -1.92652 | 1 |
| cpt | true | -1.22978 | 1 |
| cpt | false | -1.66728 | 1 |

**original open-mask top 5:** ' false' (0.349), ' incorrect' (0.308), ' true' (0.146), ' correct' (0.069), ' accurate' (0.020)
**cpt open-mask top 5:** ' true' (0.292), ' false' (0.189), ' incorrect' (0.058), ' wrong' (0.027), ' invalid' (0.024)

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
| cpt | 1000 | -4.49670 | 1 |
| cpt | 100 | -4.55920 | 1 |
| cpt | 10 | -4.93420 | 1 |
| cpt | 1 | -5.30920 | 1 |

**original open-mask top 5:** ' 1' (0.425), ' 2' (0.065), ' 10' (0.054), ' 100' (0.037), ' 3' (0.027)
**cpt open-mask top 5:** ' 200' (0.014), ' 300' (0.013), ' 500' (0.012), ' 1000' (0.011), ' 100' (0.010)

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
| cpt | 0 | -1.34262 | 1 |
| cpt | 100 | -3.28012 | 1 |
| cpt | 273.15 | -3.57686 | 3 |
| cpt | 373.15 | -3.80603 | 3 |

**original open-mask top 5:** ' 0' (0.702), ' zero' (0.108), ' 1' (0.095), ' 100' (0.021), ' 273' (0.009)
**cpt open-mask top 5:** ' 0' (0.261), ' 300' (0.058), ' 1' (0.055), ' 100' (0.038), ' 1000' (0.035)

## materials-percent-basis — Materials reasoning

Atomic percent and weight percent are interchangeable without accounting for atomic masses. This statement is {answer}.

Expected: false

Always specify the composition basis. The ratio checker does not convert wt.% to at.%.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -2.25579 | 1 |
| original | true | -4.69329 | 1 |
| cpt | true | -1.81343 | 1 |
| cpt | false | -2.56343 | 1 |

**original open-mask top 5:** ' incorrect' (0.323), ' inaccurate' (0.152), ' misleading' (0.119), ' false' (0.105), ' erroneous' (0.041)
**cpt open-mask top 5:** ' true' (0.163), ' false' (0.077), ' invalid' (0.068), ' fulfilled' (0.034), ' valid' (0.030)

## general-agreement — General English

Yesterday, the researchers {answer} their results at the meeting.

Expected: presented

Past-tense grammatical agreement; a lightweight language diagnostic.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | presented | -0.25162 | 1 |
| original | presenting | -8.37662 | 1 |
| original | presents | -11.31412 | 1 |
| cpt | presented | -1.32109 | 1 |
| cpt | presenting | -5.63359 | 1 |
| cpt | presents | -6.00859 | 1 |

**original open-mask top 5:** ' presented' (0.778), ' announced' (0.093), ' discussed' (0.027), ' reported' (0.013), ' shared' (0.010)
**cpt open-mask top 5:** ' present' (0.499), ' presented' (0.267), ' reported' (0.046), ' discussed' (0.041), ' discuss' (0.028)

## general-plural — General English

The plural of child is {answer}.

Expected: children

Irregular plural control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | children | -1.32780 | 1 |
| original | child | -1.51530 | 1 |
| original | childs | -2.81109 | 2 |
| cpt | child | -3.23552 | 1 |
| cpt | children | -3.79802 | 1 |
| cpt | childs | -5.21432 | 2 |

**original open-mask top 5:** ' children' (0.265), ' child' (0.220), ' baby' (0.028), ' boy' (0.010), ' kids' (0.009)
**cpt open-mask top 5:** ' child' (0.039), ' children' (0.022), ' called' (0.013), ' defined' (0.012), ' used' (0.009)

## general-antonym — General English

The opposite of hot is {answer}.

Expected: cold

Common lexical contrast; not a domain-specific materials question.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | cold | -0.34731 | 1 |
| original | warm | -3.97231 | 1 |
| original | bright | -8.97231 | 1 |
| cpt | cold | -2.05127 | 1 |
| cpt | warm | -4.92627 | 1 |
| cpt | bright | -7.20752 | 1 |

**original open-mask top 5:** ' cold' (0.707), ' cool' (0.108), ' warm' (0.019), ' dry' (0.015), ' sour' (0.008)
**cpt open-mask top 5:** ' cold' (0.129), ' observed' (0.069), ' expected' (0.037), ' obvious' (0.035), ' true' (0.033)

## general-object-use — General English

To protect herself from the rain, Maya opened her {answer}.

Expected: umbrella

Everyday contextual completion.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | umbrella | -1.98161 | 1 |
| original | notebook | -7.60661 | 1 |
| original | oven | -8.66911 | 1 |
| cpt | umbrella | -3.89272 | 1 |
| cpt | oven | -6.64272 | 1 |
| cpt | notebook | -7.58022 | 1 |

**original open-mask top 5:** ' eyes' (0.292), ' umbrella' (0.138), ' window' (0.138), ' mouth' (0.057), ' arms' (0.054)
**cpt open-mask top 5:** ' eyes' (0.300), ' window' (0.142), ' mouth' (0.110), ' windows' (0.034), ' umbrella' (0.020)

## general-entailment — General English

Every robin in this story is a bird. A robin named Pip appears in the story. Therefore, Pip is a {answer}.

Expected: bird

Simple entailment stated in the context; cloze preference is not proof of general reasoning ability.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | bird | -0.56080 | 1 |
| original | fish | -5.74830 | 1 |
| original | stone | -11.68580 | 1 |
| cpt | bird | -0.20510 | 1 |
| cpt | fish | -5.26760 | 1 |
| cpt | stone | -8.64260 | 1 |

**original open-mask top 5:** ' bird' (0.571), ' rabbit' (0.099), ' dog' (0.044), ' cat' (0.024), ' rodent' (0.018)
**cpt open-mask top 5:** ' bird' (0.815), ' human' (0.016), ' worm' (0.011), ' dog' (0.011), ' rodent' (0.010)

## general-negation — General English

The box is empty. The statement 'the box contains a book' is {answer}.

Expected: false

Negation control; pairs with true/false scientific probes to expose answer-label bias.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | true | -0.19922 | 1 |
| original | false | -2.82422 | 1 |
| cpt | false | -1.22584 | 1 |
| cpt | true | -1.47584 | 1 |

**original open-mask top 5:** ' true' (0.819), ' false' (0.059), ' correct' (0.046), ' incorrect' (0.032), ' proved' (0.010)
**cpt open-mask top 5:** ' false' (0.294), ' true' (0.229), ' invalid' (0.108), ' incorrect' (0.051), ' correct' (0.031)

## general-positive-control — General English

The box contains a book. The statement 'the box is empty' is false, and the statement 'a book is inside the box' is {answer}.

Expected: true

Positive-label control: always preferring 'false' is not reliable reasoning.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | true | -0.05242 | 1 |
| original | false | -3.80242 | 1 |
| cpt | true | -0.08266 | 1 |
| cpt | false | -3.45766 | 1 |

**original open-mask top 5:** ' true' (0.949), ' false' (0.022), ' correct' (0.014), ' valid' (0.005), ' True' (0.004)
**cpt open-mask top 5:** ' true' (0.921), ' false' (0.032), ' correct' (0.015), ' valid' (0.005), ' reasonable' (0.003)

## general-word-order — General English

The strings ABC and CBA contain the same letters but arrange them in a different {answer}.

Expected: order

String order matters for strings, whereas element order alone does not change normalized composition.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | order | -0.55796 | 1 |
| original | color | -9.99546 | 1 |
| original | temperature | -17.01108 | 1 |
| cpt | order | -3.06188 | 1 |
| cpt | color | -9.43688 | 1 |
| cpt | temperature | -14.34313 | 1 |

**original open-mask top 5:** ' order' (0.572), ' way' (0.347), ' manner' (0.028), ' sequence' (0.013), ' position' (0.005)
**cpt open-mask top 5:** ' way' (0.646), ' manner' (0.127), ' sequence' (0.053), ' order' (0.047), ' fashion' (0.030)

## general-synonym — General English

In the sentence 'the task was difficult', a suitable synonym for difficult is {answer}.

Expected: challenging

Vocabulary probe with a potentially multi-subword answer.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | challenging | -3.39076 | 1 |
| original | effortless | -6.75373 | 2 |
| original | wooden | -9.64076 | 1 |
| cpt | challenging | -5.56263 | 1 |
| cpt | effortless | -9.51845 | 2 |
| cpt | wooden | -13.04700 | 1 |

**original open-mask top 5:** ' difficult' (0.234), ' impossible' (0.052), ' challenging' (0.034), ' hard' (0.023), ' difficulty' (0.017)
**cpt open-mask top 5:** ' required' (0.237), ' needed' (0.223), ' lacking' (0.105), ' missing' (0.082), ' necessary' (0.039)

## alloy-order-refractory — Alloy equivalence

Assuming omitted coefficients are one and all coefficients denote atomic ratios, the refractory alloy MoNbTaVW and the reordered spelling WVTaNbMo have the {answer} normalized elemental composition.

Expected: same

Element order in a simple formula does not change normalized composition. MoNbTaVW and MoNbTaW are Senkov-type refractory alloys reported in the HEA literature.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.00375 | 1 |
| original | different | -10.31625 | 1 |
| cpt | same | -0.02179 | 1 |
| cpt | different | -10.27179 | 1 |

**original open-mask top 5:** ' same' (0.996), ' identical' (0.002), ' correct' (0.000), ' following' (0.000), ' equivalent' (0.000)
**cpt open-mask top 5:** ' same' (0.978), ' identical' (0.010), ' similar' (0.003), ' highest' (0.001), ' equivalent' (0.001)

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
| cpt | same | -3.80926 | 1 |
| cpt | different | -7.49676 | 1 |

**original open-mask top 5:** ' same' (0.247), ' total' (0.062), ' average' (0.043), ' resulting' (0.033), ' corresponding' (0.033)
**cpt open-mask top 5:** ' ideal' (0.088), ' average' (0.060), ' best' (0.060), ' optimal' (0.057), ' final' (0.034)

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
| cpt | different | -2.65182 | 1 |
| cpt | same | -5.40182 | 1 |

**original open-mask top 5:** ' different' (0.201), ' similar' (0.167), ' the' (0.147), ' identical' (0.061), ' their' (0.054)
**cpt open-mask top 5:** ' similar' (0.521), ' the' (0.103), ' different' (0.071), ' identical' (0.048), ' comparable' (0.019)

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
| cpt | same | -2.88846 | 1 |
| cpt | different | -7.51346 | 1 |

**original open-mask top 5:** ' following' (0.249), ' total' (0.117), ' resulting' (0.063), ' above' (0.059), ' same' (0.041)
**cpt open-mask top 5:** ' final' (0.118), ' same' (0.056), ' total' (0.052), ' ideal' (0.049), ' corresponding' (0.043)

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
| cpt | same | -0.02043 | 1 |
| cpt | different | -9.20793 | 1 |

**original open-mask top 5:** ' same' (0.984), ' following' (0.002), ' identical' (0.002), ' above' (0.001), ' corresponding' (0.001)
**cpt open-mask top 5:** ' same' (0.980), ' identical' (0.005), ' actual' (0.003), ' exact' (0.001), ' above' (0.001)

## notation-hyphen-list — Alloy notation

A paper writes an alloy as the hyphen-separated element list Co-Cr-Fe-Mn-Ni, and another paper writes the compact formula CoCrFeMnNi. These denote the {answer} nominal alloy composition.

Expected: same

Hyphen-separated element symbols give the same composition as the compact formula. Hand-annotated; the parser accepts no separators.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.04710 | 1 |
| original | different | -6.98460 | 1 |
| cpt | same | -0.15246 | 1 |
| cpt | different | -6.15246 | 1 |

**original open-mask top 5:** ' same' (0.954), ' corresponding' (0.004), ' exact' (0.003), ' equivalent' (0.002), ' identical' (0.002)
**cpt open-mask top 5:** ' same' (0.859), ' actual' (0.012), ' exact' (0.009), ' corresponding' (0.007), ' identical' (0.007)

## notation-hec-expanded — Alloy notation

For high-entropy carbide notation, the group formula (Hf0.2Zr0.2Ta0.2Nb0.2Ti0.2)C and the expanded formula Hf0.2Zr0.2Ta0.2Nb0.2Ti0.2C1 have the {answer} normalized elemental composition.

Expected: same

The group notation lists one fifth of each metal before one carbon; expanding the group and dividing by the total gives the same composition. (Hf,Zr,Ta,Nb,Ti)C carbides are reported in the HEC literature.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.01307 | 1 |
| original | different | -8.70057 | 1 |
| cpt | same | -0.03509 | 1 |
| cpt | different | -8.59759 | 1 |

**original open-mask top 5:** ' same' (0.987), ' following' (0.004), ' identical' (0.001), ' corresponding' (0.001), ' correct' (0.001)
**cpt open-mask top 5:** ' same' (0.966), ' similar' (0.009), ' identical' (0.009), ' highest' (0.002), ' equivalent' (0.001)

Deterministic composition reference: True
Equal atomic ratios do not establish equal microstructure or properties.

## notation-hec-substoichiometric — Alloy notation

As group formulas, (Nb0.2Ta0.2Ti0.2W0.2Zr0.2)C and the carbon-deficient (Nb0.2Ta0.2Ti0.2W0.2Zr0.2)C0.5 have {answer} normalized elemental compositions.

Expected: different

With the metal group identical, halving the carbon coefficient halves the carbon share, so the normalized compositions differ. The (Nb,Ta,Ti,W,Zr)C system is studied with non-stoichiometric carbon in real HEC experiments.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -3.26987 | 1 |
| original | same | -4.64487 | 1 |
| cpt | different | -3.99841 | 1 |
| cpt | same | -5.56091 | 1 |

**original open-mask top 5:** ' the' (0.205), ' similar' (0.125), ' their' (0.110), ' identical' (0.071), ' been' (0.063)
**cpt open-mask top 5:** ' the' (0.444), ' similar' (0.210), ' been' (0.064), ' their' (0.032), ' identical' (0.027)

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
| cpt | different | -3.26002 | 1 |
| cpt | same | -4.38502 | 1 |

**original open-mask top 5:** ' different' (0.226), ' the' (0.176), ' identical' (0.094), ' similar' (0.088), ' their' (0.069)
**cpt open-mask top 5:** ' similar' (0.468), ' the' (0.221), ' identical' (0.067), ' different' (0.038), ' same' (0.012)

Deterministic composition reference: False
Equal atomic ratios do not establish equal microstructure or properties.

## notation-group-expansion — Alloy notation

Expanding the group, the notation (Mg0.2Co0.2Ni0.2Cu0.2Zn0.2)O and the flat formula Mg0.2Co0.2Ni0.2Cu0.2Zn0.2O1 have the {answer} normalized elemental composition.

Expected: same

A parenthesized group distributes its outer coefficient over every inner coefficient, so the group notation and the flat expansion denote the same composition. (Mg0.2Co0.2Ni0.2Cu0.2Zn0.2)O is the first reported entropy-stabilized oxide (Rost et al., Nat. Commun. 6:8485, 2015).

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.05237 | 1 |
| original | different | -8.80237 | 1 |
| cpt | same | -0.05107 | 1 |
| cpt | different | -8.73857 | 1 |

**original open-mask top 5:** ' same' (0.949), ' following' (0.025), ' correct' (0.006), ' above' (0.001), ' given' (0.001)
**cpt open-mask top 5:** ' same' (0.950), ' identical' (0.007), ' similar' (0.007), ' highest' (0.006), ' most' (0.002)

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
| cpt | same | -0.08176 | 1 |
| cpt | different | -7.01926 | 1 |

**original open-mask top 5:** ' same' (0.942), ' exact' (0.009), ' identical' (0.006), ' different' (0.006), ' correct' (0.002)
**cpt open-mask top 5:** ' same' (0.921), ' exact' (0.012), ' identical' (0.010), ' similar' (0.006), ' actual' (0.005)

## notation-invar-rounded — Alloy notation

An Invar specimen listed as Fe64Ni36 at.% and the same specimen listed as about Fe63Ni37 wt.% have the {answer} elemental composition.

Expected: same

Fe64Ni36 at.% converts to about 62.85/37.15 wt.%, which rounds to Fe63Ni37 wt.% at two significant figures; quoted compositions are routinely rounded. Hand-annotated.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.01245 | 1 |
| original | different | -8.07495 | 1 |
| cpt | same | -0.19258 | 1 |
| cpt | different | -6.00508 | 1 |

**original open-mask top 5:** ' same' (0.988), ' identical' (0.007), ' correct' (0.001), ' similar' (0.001), ' following' (0.001)
**cpt open-mask top 5:** ' same' (0.825), ' similar' (0.099), ' identical' (0.039), ' different' (0.002), ' exact' (0.002)

## notation-basis-mismatch — Alloy notation

An alloy described as Fe64Ni36 in atomic percent and an alloy described as Fe64Ni36 in weight percent have {answer} normalized elemental compositions.

Expected: different

64 and 36 read as weight percent convert to about 65.1 and 34.9 at.% because the atomic masses differ, so the same numerals on different bases denote different compositions. Hand-annotated.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -0.80594 | 1 |
| original | same | -4.99344 | 1 |
| cpt | different | -3.04411 | 1 |
| cpt | same | -6.04411 | 1 |

**original open-mask top 5:** ' different' (0.447), ' identical' (0.128), ' similar' (0.113), ' the' (0.078), ' been' (0.053)
**cpt open-mask top 5:** ' the' (0.188), ' been' (0.188), ' similar' (0.166), ' their' (0.166), ' different' (0.048)

## notation-ti64-basis — Alloy notation

In the alloy Ti-6Al-4V the numerals 6 and 4 are aluminium and vanadium in weight percent. A description with 6 and 4 as aluminium and vanadium in atomic percent defines {answer} alloy composition from Ti-6Al-4V.

Expected: different

Ti-6Al-4V uses weight percent: 6 wt.% Al and 4 wt.% V correspond to about 10.2 and 3.6 at.% on a roughly 86.2 at.% Ti balance, not 6 and 4 at.%. Hand-annotated; hyphenated designations and bases are outside the parser.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -6.98099 | 1 |
| original | same | -9.85599 | 1 |
| cpt | different | -6.34461 | 1 |
| cpt | same | -9.28211 | 1 |

**original open-mask top 5:** ' the' (0.845), ' an' (0.069), ' this' (0.048), ' its' (0.014), ' their' (0.006)
**cpt open-mask top 5:** ' the' (0.803), ' this' (0.085), ' an' (0.058), ' its' (0.020), ' another' (0.006)

## science-ideal-gas-product — Scientific reasoning (non-materials)

For a fixed amount of an ideal gas, the state with pressure 2P and volume V and the state with pressure P and volume 2V have the {answer} pressure-volume product.

Expected: same

Both products equal 2PV. Elementary gas-law reasoning placed outside materials science; a paired control for scientific reading without alloy vocabulary.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.01504 | 1 |
| original | different | -8.76504 | 1 |
| cpt | same | -0.08407 | 1 |
| cpt | different | -8.52157 | 1 |

**original open-mask top 5:** ' same' (0.985), ' identical' (0.002), ' opposite' (0.001), ' equal' (0.001), ' corresponding' (0.001)
**cpt open-mask top 5:** ' same' (0.919), ' largest' (0.014), ' highest' (0.012), ' maximum' (0.006), ' lowest' (0.004)

## science-ideal-gas-energy — Scientific reasoning (non-materials)

For a fixed amount of monatomic ideal gas heated by 10 kelvin, the constant-volume path and the constant-pressure path give the {answer} internal energy change.

Expected: same

U = (3/2) n R T depends only on temperature, so equal temperature rises give equal internal energy changes; the heat supplied differs because constant-pressure heating also does expansion work.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | same | -0.37199 | 1 |
| original | different | -7.80949 | 1 |
| cpt | same | -0.54627 | 1 |
| cpt | different | -6.42127 | 1 |

**original open-mask top 5:** ' same' (0.689), ' total' (0.025), ' corresponding' (0.021), ' average' (0.020), ' net' (0.014)
**cpt open-mask top 5:** ' same' (0.579), ' largest' (0.114), ' maximum' (0.051), ' highest' (0.035), ' lowest' (0.033)

## science-isotope-control — Scientific reasoning (non-materials)

One mole of ordinary water H2O and one mole of heavy water D2O have {answer} molar masses.

Expected: different

Negative control: D2O weighs about one gram more per mole than H2O because deuterium is roughly twice as heavy as hydrogen. Chemistry outside alloy-composition reasoning.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | different | -2.15263 | 1 |
| original | same | -4.21513 | 1 |
| cpt | different | -2.81299 | 1 |
| cpt | same | -4.43799 | 1 |

**original open-mask top 5:** ' equal' (0.406), ' opposite' (0.132), ' different' (0.116), ' similar' (0.055), ' identical' (0.048)
**cpt open-mask top 5:** ' equal' (0.368), ' similar' (0.324), ' different' (0.060), ' identical' (0.028), ' comparable' (0.022)

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
| cpt | five | -0.36303 | 1 |
| cpt | seven | -4.98803 | 1 |
| cpt | two | -7.36303 | 1 |
| cpt | twenty | -9.73803 | 1 |

**original open-mask top 5:** ' three' (0.192), ' two' (0.169), ' four' (0.132), ' six' (0.091), ' five' (0.055)
**cpt open-mask top 5:** ' five' (0.696), ' four' (0.226), ' three' (0.024), ' six' (0.019), ' 5' (0.011)

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
| cpt | 1.6 | -1.01925 | 3 |
| cpt | 2.5 | -1.06091 | 3 |
| cpt | 0.8 | -2.35258 | 3 |
| cpt | 5.0 | -3.43591 | 3 |

**original open-mask top 5:** ' three' (0.088), ' 10' (0.064), ' 5' (0.064), ' two' (0.064), ' five' (0.060)
**cpt open-mask top 5:** ' 5' (0.215), ' five' (0.148), ' 10' (0.070), ' four' (0.042), ' three' (0.033)

## hea-cantor-fcc — HEA knowledge

At room temperature the conventional Cantor alloy CoCrFeMnNi is reported to form a predominantly {answer} solid-solution structure.

Expected: FCC

Canonical experimental result for equiatomic CoCrFeMnNi as reported in the founding Cantor et al. 2004 work. Known material fact, not a prediction for an arbitrary alloy.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | FCC | -8.42719 | 1 |
| original | BCC | -9.13072 | 2 |
| cpt | FCC | -0.04727 | 1 |
| cpt | BCC | -0.57953 | 2 |

**original open-mask top 5:** ' cubic' (0.576), ' amorphous' (0.047), ' metallic' (0.022), ' crystalline' (0.021), ' planar' (0.021)
**cpt open-mask top 5:** ' FCC' (0.954), ' disordered' (0.029), ' single' (0.003), ' amorphous' (0.003), ' ordered' (0.002)

## hea-refractory-bcc — HEA knowledge

The refractory alloys MoNbTaW and MoNbTaVW are reported to form predominantly {answer} solid-solution structures at room temperature.

Expected: BCC

Canonical Senkov-type refractory HEA behaviour. Kept as a paired control so neither phase abbreviation is always favored.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | FCC | -8.94368 | 1 |
| original | BCC | -9.75017 | 2 |
| cpt | BCC | -0.27021 | 2 |
| cpt | FCC | -1.16433 | 1 |

**original open-mask top 5:** ' in' (0.173), ' amorphous' (0.119), ' cubic' (0.105), ' crystalline' (0.053), ' as' (0.023)
**cpt open-mask top 5:** ' FCC' (0.312), ' simple' (0.215), ' disordered' (0.147), ' single' (0.079), ' random' (0.061)

## hea-aluminium-bcc-trend — HEA knowledge

In the AlxCoCrFeNi family, increasing the aluminium fraction progressively shifts the reported microstructure from FCC toward {answer}.

Expected: BCC

Empirically established directional trend in the real AlxCoCrFeNi system; a trend statement, not a phase predictor for one specific sample.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | FCC | -1.21984 | 1 |
| original | BCC | -3.94687 | 2 |
| cpt | BCC | -0.34535 | 2 |
| cpt | FCC | -1.81132 | 1 |

**original open-mask top 5:** ' FCC' (0.295), ' ABC' (0.062), ' AFM' (0.017), ' Fe' (0.015), ' amorphous' (0.014)
**cpt open-mask top 5:** ' amorphous' (0.444), ' FCC' (0.163), ' σ' (0.112), ' dendritic' (0.028), ' B' (0.021)

## hea-interstitial-solutes — HEA knowledge

Carbon and oxygen in high-entropy alloys are conventionally classed as {answer} solute atoms rather than principal components.

Expected: interstitial

Small non-metal atoms occupy interstitial sites; interstitial-engineered HEAs are a recognized subfield.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | principal | -1.86491 | 1 |
| original | interstitial | -8.42741 | 1 |
| cpt | interstitial | -2.32620 | 1 |
| cpt | principal | -5.70120 | 1 |

**original open-mask top 5:** ' the' (0.255), ' principal' (0.155), ' individual' (0.029), ' primary' (0.027), ' constituent' (0.025)
**cpt open-mask top 5:** ' minor' (0.283), ' interstitial' (0.098), ' the' (0.052), ' additional' (0.041), ' major' (0.025)

## materials-sem — Materials terminology

Scanning electron microscopy is commonly abbreviated as {answer}.

Expected: SEM

Microscopy abbreviation control, matching the XRD probe.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | SEM | -0.07486 | 1 |
| original | STM | -4.07486 | 1 |
| original | SXRD | -5.51750 | 3 |
| cpt | SEM | -0.14496 | 1 |
| cpt | SXRD | -5.54070 | 3 |
| cpt | STM | -6.95746 | 1 |

**original open-mask top 5:** ' SEM' (0.928), ' STEM' (0.036), ' STM' (0.017), 'SEM' (0.012), ' microscopy' (0.001)
**cpt open-mask top 5:** ' SEM' (0.865), ' STEM' (0.103), ' microscopy' (0.007), ' TEM' (0.006), 'SEM' (0.004)

## materials-tem — Materials terminology

Transmission electron microscopy is commonly abbreviated as {answer}.

Expected: TEM

A third microscopy abbreviation control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | TEM | -0.67180 | 1 |
| original | STM | -3.67180 | 1 |
| original | TGA | -8.18061 | 2 |
| cpt | TEM | -0.14242 | 1 |
| cpt | TGA | -4.86467 | 2 |
| cpt | STM | -7.64242 | 1 |

**original open-mask top 5:** ' TEM' (0.511), ' STEM' (0.451), ' STM' (0.025), 'TEM' (0.005), ' SEM' (0.002)
**cpt open-mask top 5:** ' TEM' (0.867), ' STEM' (0.117), 'TEM' (0.006), ' transmission' (0.002), ' SEM' (0.001)

## materials-eds — Materials terminology

Energy-dispersive X-ray spectroscopy is commonly abbreviated as {answer}.

Expected: EDS

Chemistry-characterization abbreviation; WDS is a distinct spectroscopy mode, not the same abbreviation.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | EDS | -2.58149 | 2 |
| original | WDS | -8.70649 | 2 |
| original | STM | -10.49866 | 1 |
| cpt | EDS | -0.80671 | 2 |
| cpt | WDS | -6.08796 | 2 |
| cpt | STM | -9.23567 | 1 |

**original open-mask top 5:** ' ESR' (0.733), ' AES' (0.028), ' ED' (0.027), ' DES' (0.020), ' EMS' (0.018)
**cpt open-mask top 5:** ' AES' (0.226), ' TEM' (0.078), ' spectroscopy' (0.069), ' STEM' (0.057), ' SEM' (0.047)

## materials-dsc — Materials terminology

Differential scanning calorimetry is commonly abbreviated as {answer}.

Expected: DSC

Thermal-analysis abbreviation control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | DSC | -0.25873 | 2 |
| original | DSX | -6.94623 | 2 |
| original | SAM | -15.94912 | 1 |
| cpt | DSC | -0.00727 | 2 |
| cpt | DSX | -10.28852 | 2 |
| cpt | SAM | -14.43367 | 1 |

**original open-mask top 5:** ' DNS' (0.453), ' DEC' (0.147), ' dc' (0.061), ' DSS' (0.054), ' DC' (0.048)
**cpt open-mask top 5:** ' DAC' (0.336), ' DSS' (0.109), ' DC' (0.109), ' DEC' (0.096), ' DD' (0.096)

## materials-vickers-hv — Materials terminology

Vickers hardness is denoted by the symbol {answer}.

Expected: HV

HV is Vickers; HB and HRC denote Brinell and Rockwell C scales. Relevant because HEA papers report HV values.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | HV | -3.46464 | 1 |
| original | HRC | -5.56122 | 2 |
| original | HB | -6.21464 | 1 |
| cpt | HV | -1.49207 | 1 |
| cpt | HRC | -6.08827 | 2 |
| cpt | HB | -6.61707 | 1 |

**original open-mask top 5:** ' V' (0.432), ' H' (0.080), ' v' (0.043), ' HV' (0.031), ' K' (0.024)
**cpt open-mask top 5:** ' V' (0.420), ' HV' (0.225), ' H' (0.094), ' K' (0.018), ' M' (0.016)

## materials-bragg-angle — Materials terminology

For a fixed X-ray wavelength, increasing the lattice parameter shifts diffraction peaks toward {answer} diffraction angles.

Expected: lower

Bragg's law: larger d needs smaller theta at fixed wavelength; complementary to the XRD abbreviation probe.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | higher | -1.24080 | 1 |
| original | lower | -2.11580 | 1 |
| cpt | lower | -0.56437 | 1 |
| cpt | higher | -1.18937 | 1 |

**original open-mask top 5:** ' higher' (0.289), ' larger' (0.155), ' smaller' (0.137), ' lower' (0.121), ' shorter' (0.039)
**cpt open-mask top 5:** ' lower' (0.569), ' higher' (0.304), ' larger' (0.047), ' smaller' (0.032), ' broader' (0.008)

## materials-strain-rate — Materials reasoning

Two identical specimens of the same alloy tension-tested at different strain rates can show different measured strengths. This statement is {answer}.

Expected: true

Rate sensitivity is routinely observed; 'can show' keeps the claim weak and true.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -0.93602 | 1 |
| original | true | -2.18602 | 1 |
| cpt | false | -1.18304 | 1 |
| cpt | true | -2.62054 | 1 |

**original open-mask top 5:** ' false' (0.392), ' incorrect' (0.270), ' true' (0.112), ' correct' (0.032), ' erroneous' (0.022)
**cpt open-mask top 5:** ' false' (0.306), ' invalid' (0.088), ' incorrect' (0.082), ' true' (0.073), ' erroneous' (0.044)

## materials-grain-size — Materials reasoning

For many crystalline materials, finer grains give higher room-temperature yield strength. This statement is {answer}.

Expected: true

Grain-boundary (Hall-Petch-type) strengthening is a standard effect; 'many' avoids a universal claim.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.18114 | 1 |
| original | true | -1.55614 | 1 |
| cpt | true | -1.69856 | 1 |
| cpt | false | -3.13606 | 1 |

**original open-mask top 5:** ' false' (0.307), ' true' (0.211), ' incorrect' (0.186), ' negative' (0.060), ' accurate' (0.047)
**cpt open-mask top 5:** ' true' (0.183), ' contradictory' (0.072), ' controversial' (0.067), ' false' (0.043), ' incorrect' (0.041)

## materials-solute-strengthening — Materials reasoning

Adding substitutional solute atoms usually increases a metal's yield strength by impeding dislocation motion. This statement is {answer}.

Expected: true

Solid-solution strengthening is a standard mechanism; 'usually' avoids a universal claim.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.13024 | 1 |
| original | true | -1.63024 | 1 |
| cpt | true | -0.75765 | 1 |
| cpt | false | -2.88265 | 1 |

**original open-mask top 5:** ' false' (0.323), ' incorrect' (0.252), ' true' (0.196), ' correct' (0.050), ' negative' (0.034)
**cpt open-mask top 5:** ' true' (0.469), ' false' (0.056), ' incorrect' (0.036), ' contradictory' (0.025), ' correct' (0.023)

## materials-temperature-softening — Materials reasoning

A compression specimen tested at 500 degrees Celsius is expected to show essentially the same yield strength as one tested at 25 degrees Celsius. This statement is {answer}.

Expected: false

Thermal softening generally reduces high-temperature strength; this contrasts with the isothermal unit-conversion probes. This is why test temperature must accompany every strength value.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.22690 | 1 |
| original | true | -2.35190 | 1 |
| cpt | true | -1.87055 | 1 |
| cpt | false | -2.43305 | 1 |

**original open-mask top 5:** ' incorrect' (0.332), ' false' (0.293), ' true' (0.095), ' correct' (0.074), ' erroneous' (0.045)
**cpt open-mask top 5:** ' true' (0.154), ' false' (0.088), ' incorrect' (0.060), ' unreasonable' (0.057), ' reasonable' (0.039)

## materials-property-independence — Materials reasoning

One measured mechanical property such as hardness is sufficient to determine a different property such as corrosion resistance. This statement is {answer}.

Expected: false

Distinct material properties require separate measurements; extends the hardness-not-strength control across property families.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | false | -1.29954 | 1 |
| original | true | -2.54954 | 1 |
| cpt | false | -1.88701 | 1 |
| cpt | true | -3.44951 | 1 |

**original open-mask top 5:** ' incorrect' (0.309), ' false' (0.273), ' true' (0.078), ' correct' (0.069), ' erroneous' (0.037)
**cpt open-mask top 5:** ' incorrect' (0.172), ' false' (0.152), ' invalid' (0.098), ' erroneous' (0.092), ' unreasonable' (0.041)

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
| cpt | 0.002 | -3.46050 | 3 |
| cpt | 200 | -4.18861 | 1 |
| cpt | 20 | -5.12611 | 1 |
| cpt | 2000 | -5.56361 | 1 |

**original open-mask top 5:** ' 2' (0.230), ' 1' (0.085), ' 4' (0.075), ' 3' (0.062), ' 10' (0.045)
**cpt open-mask top 5:** ' 200' (0.015), ' 300' (0.013), ' 500' (0.011), ' 400' (0.010), ' 100' (0.009)

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
| cpt | 1 | -2.94036 | 1 |
| cpt | 10 | -2.94036 | 1 |
| cpt | 100 | -4.31536 | 1 |
| cpt | 1000 | -6.19036 | 1 |

**original open-mask top 5:** ' 1000' (0.315), ' 1' (0.149), ' 10' (0.058), ' 100' (0.055), ' 2' (0.023)
**cpt open-mask top 5:** ' 1' (0.053), ' 10' (0.053), ' 2' (0.041), ' 5' (0.030), ' 3' (0.027)

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
| cpt | 100 | -2.07134 | 1 |
| cpt | 0 | -2.25884 | 1 |
| cpt | 273.15 | -3.60971 | 3 |
| cpt | 373.15 | -3.79721 | 3 |

**original open-mask top 5:** ' 100' (0.285), ' 1' (0.252), ' 0' (0.105), ' 101' (0.064), ' one' (0.034)
**cpt open-mask top 5:** ' 100' (0.126), ' 0' (0.104), ' 1' (0.060), ' 105' (0.049), ' 300' (0.049)

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
| cpt | 0 | -2.19512 | 1 |
| cpt | 100 | -3.38262 | 1 |
| cpt | 273.15 | -3.70025 | 3 |
| cpt | -273.15 | -4.93017 | 4 |

**original open-mask top 5:** ' 0' (0.863), ' zero' (0.033), ' 100' (0.020), ' 273' (0.010), ' 10' (0.007)
**cpt open-mask top 5:** ' 0' (0.111), ' 10' (0.044), ' 20' (0.038), ' 2' (0.038), ' 100' (0.034)

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
| cpt | 4 | -1.64989 | 1 |
| cpt | 40 | -3.71239 | 1 |
| cpt | 400 | -7.21239 | 1 |
| cpt | 19 | -9.08739 | 1 |

**original open-mask top 5:** ' 4' (0.341), ' one' (0.161), ' 1' (0.161), ' four' (0.059), ' an' (0.041)
**cpt open-mask top 5:** ' one' (0.204), ' 4' (0.192), ' 1' (0.116), ' the' (0.075), ' four' (0.049)

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
| cpt | 30 | -2.88212 | 1 |
| cpt | 3 | -3.81962 | 1 |
| cpt | 29 | -6.31962 | 1 |
| cpt | 0.3 | -7.89792 | 3 |

**original open-mask top 5:** ' 30' (0.129), ' percent' (0.069), ' 100' (0.051), ' 10' (0.029), ' 1' (0.027)
**cpt open-mask top 5:** ' of' (0.092), ' 30' (0.056), ' 1' (0.038), ' 20' (0.030), ' percent' (0.026)

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
| cpt | 100 | -2.09361 | 1 |
| cpt | 20 | -2.46861 | 1 |
| cpt | 90 | -4.78111 | 1 |
| cpt | 150 | -6.15611 | 1 |

**original open-mask top 5:** ' 100' (0.375), ' 10' (0.051), ' 20' (0.035), ' 50' (0.031), ' one' (0.027)
**cpt open-mask top 5:** ' equal' (0.140), ' 100' (0.123), ' five' (0.096), ' 20' (0.085), ' 10' (0.066)

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
| cpt | 1 | -0.32316 | 1 |
| cpt | 10 | -4.82316 | 1 |
| cpt | 100 | -6.01066 | 1 |
| cpt | 1000 | -6.13566 | 1 |

**original open-mask top 5:** ' 1' (0.716), ' one' (0.263), ' a' (0.008), ' 1000' (0.002), ' 100' (0.001)
**cpt open-mask top 5:** ' 1' (0.724), ' one' (0.207), ' a' (0.032), ' 10' (0.008), ' 100' (0.002)

## general-strength-comparative — General English

Two alloy samples have tensile strengths of 800 MPa and 1200 MPa. The sample with 1200 MPa is {answer}.

Expected: stronger

Comparative-adjective probe built on plain numbers; combines language with an arithmetic-free comparison.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | stronger | -5.74919 | 1 |
| original | softer | -7.18669 | 1 |
| cpt | stronger | -2.02034 | 1 |
| cpt | softer | -3.27034 | 1 |

**original open-mask top 5:** ' used' (0.120), ' shown' (0.053), ' tested' (0.032), ' selected' (0.027), ' thicker' (0.025)
**cpt open-mask top 5:** ' stronger' (0.133), ' fractured' (0.103), ' harder' (0.076), ' better' (0.076), ' softer' (0.038)

## general-hardness-superlative — General English

Three samples have hardness 200 HV, 300 HV and 700 HV. The sample with 700 HV is the {answer}.

Expected: hardest

Superlative-adjective probe with the largest value uniquely identified.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | hardest | -4.67146 | 1 |
| original | softest | -5.03698 | 2 |
| cpt | hardest | -0.35760 | 1 |
| cpt | softest | -3.13910 | 2 |

**original open-mask top 5:** ' best' (0.374), ' largest' (0.121), ' highest' (0.051), ' strongest' (0.045), ' oldest' (0.045)
**cpt open-mask top 5:** ' hardest' (0.699), ' highest' (0.065), ' best' (0.065), ' strongest' (0.051), ' harder' (0.019)

## general-above-higher — General English

A temperature described as above 300 kelvin is {answer} than 300 kelvin.

Expected: higher

Spatial preposition control; complements the antonym and word-order probes.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | higher | -1.92589 | 1 |
| original | lower | -4.42589 | 1 |
| cpt | lower | -1.09455 | 1 |
| cpt | higher | -1.34455 | 1 |

**original open-mask top 5:** ' greater' (0.576), ' higher' (0.146), ' more' (0.114), ' less' (0.069), ' warmer' (0.047)
**cpt open-mask top 5:** ' lower' (0.335), ' higher' (0.261), ' less' (0.140), ' more' (0.066), ' greater' (0.043)

## science-boyle-law — Scientific reasoning (non-materials)

For a fixed amount of ideal gas at constant temperature, doubling the pressure halves the volume. This statement is {answer}.

Expected: true

Boyle's-law control; pairs with the pressure-volume product probe.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | true | -0.72610 | 1 |
| original | false | -1.22610 | 1 |
| cpt | true | -0.49096 | 1 |
| cpt | false | -2.49096 | 1 |

**original open-mask top 5:** ' true' (0.484), ' false' (0.293), ' incorrect' (0.108), ' negative' (0.031), ' correct' (0.027)
**cpt open-mask top 5:** ' true' (0.612), ' false' (0.083), ' valid' (0.017), ' correct' (0.016), ' incorrect' (0.014)

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
| cpt | five | -6.12675 | 1 |
| cpt | ten | -7.93925 | 1 |
| cpt | zero | -8.56425 | 1 |
| cpt | one | -9.81425 | 1 |

**original open-mask top 5:** ' 5' (0.219), ' 10' (0.151), ' 6' (0.081), ' 7' (0.055), ' 15' (0.041)
**cpt open-mask top 5:** ' 5' (0.163), ' 10' (0.099), ' 20' (0.047), ' 6' (0.047), ' 3' (0.044)

## science-heated-density — Scientific reasoning (non-materials)

At constant pressure, heating a fixed amount of ideal gas makes it {answer} dense.

Expected: less

Ideal-gas density control; directional-phrase probe like the Bragg-angle items.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | less | -0.66330 | 1 |
| original | more | -1.16330 | 1 |
| cpt | more | -1.10544 | 1 |
| cpt | less | -2.41794 | 1 |

**original open-mask top 5:** ' less' (0.515), ' more' (0.312), ' very' (0.037), ' infinitely' (0.033), ' optically' (0.008)
**cpt open-mask top 5:** ' more' (0.331), ' completely' (0.101), ' fully' (0.089), ' less' (0.089), ' become' (0.048)

## science-condensation — Scientific reasoning (non-materials)

For most substances, cooling a gas at constant pressure below its boiling temperature turns it into a {answer}.

Expected: liquid

Condensation control; 'for most substances' keeps the statement true (a minority of substances subliminate in accessible conditions).

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | liquid | -0.18553 | 1 |
| original | solid | -3.18553 | 1 |
| cpt | liquid | -0.19965 | 1 |
| cpt | solid | -2.07465 | 1 |

**original open-mask top 5:** ' liquid' (0.831), ' vapor' (0.053), ' gas' (0.047), ' solid' (0.041), ' fluid' (0.004)
**cpt open-mask top 5:** ' liquid' (0.819), ' solid' (0.126), ' vapor' (0.009), ' vacuum' (0.006), ' gas' (0.004)

## science-heat-flow-direction — Scientific reasoning (non-materials)

Heat flows spontaneously from a hotter body to a {answer} body.

Expected: colder

Everyday thermodynamics matching the internal-energy probe; no alloy vocabulary.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | colder | -0.79838 | 2 |
| original | hotter | -2.42338 | 2 |
| cpt | colder | -1.60356 | 2 |
| cpt | hotter | -2.69731 | 2 |

**original open-mask top 5:** ' cooler' (0.927), ' warmer' (0.028), ' cold' (0.022), ' cool' (0.007), ' thinner' (0.003)
**cpt open-mask top 5:** ' cooler' (0.853), ' smaller' (0.023), ' thinner' (0.021), ' cold' (0.017), ' lower' (0.014)

## science-newton-definition — Scientific reasoning (non-materials)

In SI units, one newton is the force that accelerates a one-kilogram mass at {answer} metre per square second.

Expected: one

Force-unit definition; a non-materials control for numerical staleness probes.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | one | -0.07931 | 1 |
| original | ten | -7.89181 | 1 |
| original | zero | -8.07931 | 1 |
| cpt | one | -0.07956 | 1 |
| cpt | zero | -6.39207 | 1 |
| cpt | ten | -7.95457 | 1 |

**original open-mask top 5:** ' one' (0.924), ' 1' (0.052), ' a' (0.015), ' 100' (0.000), ' per' (0.000)
**cpt open-mask top 5:** ' one' (0.924), ' a' (0.036), ' 1' (0.028), ' the' (0.003), ' zero' (0.002)

## science-archimedes — Scientific reasoning (non-materials)

An ice cube floating in a glass of water displaces a weight of water {answer} to the weight of the ice cube.

Expected: equal

Archimedes' principle for floating bodies; qualitative physics control.

| Model | Candidate | Mean log probability | Target tokens |
|---|---|---:|---:|
| original | equal | -0.08958 | 1 |
| original | double | -10.15208 | 1 |
| cpt | equal | -0.12341 | 1 |
| cpt | double | -9.49841 | 1 |

**original open-mask top 5:** ' equal' (0.914), ' proportional' (0.035), ' equivalent' (0.028), ' corresponding' (0.004), ' similar' (0.003)
**cpt open-mask top 5:** ' equal' (0.884), ' equivalent' (0.073), ' proportional' (0.016), ' similar' (0.004), ' corresponding' (0.003)
