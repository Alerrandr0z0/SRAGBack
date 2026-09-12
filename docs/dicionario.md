                                                                                                                                                          SIVEP-Gripe
                                                                                                         SISTEMA DE INFORMAÇÃO DA VIGILÂNCIA EPIDEMIOLÓGICA DA GRIPE
                                                                                                                                                                                         25/05/2023.
             MINISTÉRIO DA SAÚDE
       SECRETARIA DE VIGILÂNCIA EM SAÚDE



                                                                       Dicionário de Dados
                        FICHA DE REGISTRO INDIVIDUAL – CASOS DE SÍNDROME RESPIRATÓRIA AGUDA GRAVE HOSPITALIZADOS

Este documento tem como finalidade descrever as variáveis exportadas
para o banco de dados em DBF.

CAMPO OBRIGATÓRIO é aquele cuja ausência de dado impossibilita a
inclusão do registro no sistema. CAMPO ESSENCIAL é aquele que, apesar de
não ser obrigatório, registra dado necessário à investigação do caso ou
ao cálculo de indicador epidemiológico ou operacional. CAMPO INTERNO é
aquele que apesar de não constar na ficha e não aparecer no display da
tela, é preenchido automaticamente pelo sistema. CAMPO OPCIONAL é aquele
que só deve ser preenchido caso seja necessário, aparece no display da
tela e consta no banco de dados.

Nome do campo Tipo Categoria Descrição Características DBF Nº
Varchar2(12) Número do registro Campo Interno NU_NOTIFIC

                                                                                             Número sequencial gerado automaticamente pelo sistema.

                                                                                             Utilizar o padrão:
                                                                                             320120000123

                                                                                             Dígito 1: caracteriza o tipo da ficha (1=SG, 2=SRAG-UTI e 3-SRAG
                                                                                             Hospitalizado).

                                                                                             Dígitos 2 a 12: número sequencial gerado automaticamente pelo sistema.

1-Data do preenchimento da ficha de Date Data de Campo Obrigatório
DT_NOTIFIC notificação DD/MM/AAAA preenchimento da ficha de Data deve
ser \<= a data da digitação. notificação. Semana Epidemiológica do
Varchar2(6) Semana Campo Interno SEM_NOT preenchimento da ficha de
Epidemiológica do notificação preenchimento da Calculado a partir da
data dos Primeiros Sintomas. ficha de (SS) SIVEP Gripe- Sistema de
Informação da Vigilância Epidemiológica da Gripe. Página 1  notificação.
2-Data de 1ºs sintomas Date Data de 1º Campo Obrigatório DT_SIN_PRI
DD/MM/AAAA sintomas do caso. Data deve ser \<= a data da digitação e
data do preenchimento da ficha de notificação Semana Epidemiológica dos
Primeiros Varchar2(6) Semana Campo Interno SEM_PRI Sintomas
Epidemiológica do início dos sintomas. Calculado a partir da data dos
Primeiros Sintomas. (SS) 3-UF Varchar2(2) Tabela com código e siglas
Unidade Federativa Campo Obrigatório SG_UF_NOT das UF padronizados pelo
onde está IBGE. localizada a Se usuário que está digitando a ficha for
de nível: Unidade que  Unidade - o campo é preenchido automaticamente
pelo sistema com a realizou a UF, município e unidade onde está
cadastrado o usuário. notificação.  Municipal -- o campo é preenchido
automaticamente pelo sistema com a UF e município onde está cadastrado o
usuário.  Estadual -- o campo é preenchido automaticamente pelo sistema
com a UF do usuário.  Federal - abre tabela com todas as UF que possuam
unidades cadastradas no sistema.

4-Município Varchar2 (6) Tabela com código e nomes Município onde Campo
Obrigatório ID_MUNICIP OU Código (IBGE) dos Municípios está localizada a
CO_MUN_NOT padronizados pelo IBGE. Unidade que Preenchendo o nome do
município de notificação, o código é preenchido realizou a
automaticamente, e vice-versa; notificação. Se usuário que está
digitando a ficha for de nível:  Unidade -- o campo é preenchido
automaticamente pelo sistema com o Município onde está localizada a
unidade de notificação.  Municipal -- o campo é preenchido
automaticamente pelo sistema com o município do usuário.  Estadual ou
Federal -- abre tabela com todos os municípios da UF selecionada no
campo 3 que possuam unidades cadastradas no sistema.

Regional de Saúde de Notificação Varchar2 (6) Tabela com código e nomes
Regional de Saúde Campo Interno ID_REGIONA OU Código (IBGE) das
Regionais de Saúde dos onde está CO_REGIONA municípios de notificação
localizado o Preenchendo o nome da regional de saúde de notificação, o
código é padronizados pelo IBGE. Município realizou preenchido
automaticamente, e vice-versa; a notificação. Se usuário que está
digitando a ficha for de nível:

                                                                                                                               SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 2

 Unidade -- o campo é preenchido automaticamente pelo sistema com a
Regional do Município onde está localizada a unidade de notificação. 
Municipal -- o campo é preenchido automaticamente pelo sistema com a
regional do município do usuário.

5-Unidade de Saúde Varchar2(7) Tabela com códigos CNES e Unidade que
Campo Obrigatório ID_UNIDADE OU Código (CNES) nomes das Unidades
realizou o CO_UNI_NOT cadastradas no sistema. atendimento, Preenchendo o
nome da unidade, o código é preenchido automaticamente, coleta de
amostra e e vice-versa; registro do caso. Se usuário que está digitando
a ficha for de nível:  Unidade - o campo é preenchido automaticamente
pelo sistema.  Municipal -- abre tabela apenas com as unidades do
município.  Estadual ou Federal -- abre tabela com as unidades do
município selecionado o campo 4.

6- Tem CPF? Varchar(1) 1- Sim Informar se o Campo Obrigatório TEM_CPF
2-Não paciente notificado dispõe de Número do Cadastro de Pessoa Física
(CPF) Se selecionado "Sim", preencher campo "CPF". Se selecionado "Não"
preencher CNS. Se o paciente não dispor de CPF é obrigatório o
preenchimento do CNS. No caso de pacientes raça/cor indígenas, somente o
CNS é considerado como campo obrigatório. 7-CPF do paciente Varchar2(15)
Numérico (11 dígitos) Número do Campo Obrigatório NU_CPF Cadastro de
Pessoa Física (CPF) do Quando preenchido o número do CPF o sistema
deverá preencher o Nome, paciente notificado Sexo, Data de Nascimento,
Idade, Raça/Cor e o nome da mãe do paciente. 8- Estrangeiro Varchar(1)
1-Sim Informar se o Campo Obrigatório ESTRANG 2-Não paciente é
estrangeiro Se selecionado "Sim", o campo CPF e CNS, deixa de ser
obrigatório.

9- Cartão Nacional de Saúde (CNS) Varchar2(15) Numérico (14 dígitos)
Preencher com o Campo Obrigatório NU_CNS número do Cartão Nacional de
Saúde do paciente 10-Nome Varchar2(70) Nome completo do Campo
Obrigatório NM_PACIENT paciente (sem abreviações) 11-Sexo Varchar2 (1)
1-Masculino Sexo do paciente. Campo Obrigatório CS_SEXO

                                                                                                                         SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 3

2-Feminino 9-Ignorado 12-Data de nascimento Date Data de nascimento
Campo Essencial DT_NASC DD/MM/AAAA do paciente. Data deve ser \<= a data
dos primeiros sintomas. 13-(ou) Idade Varchar2(3) Idade informada Campo
Obrigatório NU_IDADE_N pelo paciente quando não se sabe Se digitado a
data de nascimento, a idade é calculada e preenchida a data de
automaticamente pelo sistema: considerando o intervalo entre a data de
nascimento. nascimento e a data dos primeiros sintomas.

                                                             Na falta desse dado Idade deve ser <= 150.
                                                             é registrada a idade
                                                             aparente.

(ou) Tipo/Idade Varchar2(1) 1-Dia Campo Obrigatório TP_IDADE 2-Mês 3-Ano
Se digitado a data de nascimento, o campo Idade/Tipo é calculado e
preenchido automaticamente pelo sistema: considerando o intervalo entre
a data de nascimento e a data dos primeiros sintomas.

                                                                                 Se a diferença for de 0 a 30 dias, o sistema grava em Idade = (nº dias) e em
                                                                                 Tipo = 1-Dia. Por exemplo: se Data de nascimento = 05/12/2012 e Data dos
                                                                                 1ºs sintomas = 11/12/2012, então Idade = 6 e Tipo = 1-Dia.

                                                                                 Se a diferença for de 1 a 11 meses, o sistema grava em Idade = (nº meses) e
                                                                                 em Tipo = 2-Mês. Por exemplo: se Data de nascimento = 05/10/2012 e Data
                                                                                 dos 1ºs sintomas = 11/12/2012, então Idade = 2 e Tipo = 2-Mês.

                                                                                 Se a diferença for maior ou igual a 12 meses, o sistema grava em Idade = (nº
                                                                                 anos) e em Tipo = 3-Ano. Por exemplo: se Data de nascimento = 05/10/2011
                                                                                 e Data dos 1ºs sintomas = 11/12/2012, então Idade = 1 e Tipo = 3-Ano.

14-Gestante Varchar2(1) 1-1º Trimestre Idade gestacional Campo
Obrigatório CS_GESTANT 2-2º Trimestre da paciente. 3-3º Trimestre Se
selecionado categoria 2-Feminino no campo Sexo. 4-Idade Gestacional
Ignorada Se selecionado sexo igual a Masculino ou a idade for menor ou
igual a 9 anos 5-Não o campo é preenchido automaticamente com 6-Não se
aplica. 6-Não se aplica 9-Ignorado Se selecionado sexo igual a Feminino
e idade for maior que 9 anos, o campo não pode ser preenchido com 6-Não
se aplica. 15-Raça/Cor Varchar2(2) 1-Branca Cor ou raça Campo
Obrigatório CS_RACA SIVEP Gripe- Sistema de Informação da Vigilância
Epidemiológica da Gripe. Página 4  2-Preta declarada pelo 3-Amarela
paciente: 4-Parda Branca; Preta; 5-Indígena Amarela; Parda 9-Ignorado
(pessoa que se declarou mulata, cabocla, cafuza, mameluca ou mestiça de
preto com pessoa de outra cor ou raça); e, Indígena. 16-Se indígena,
qual etnia? Varchar2(4) Tabela do SIASI com código e Nome e código da
Campo Essencial CS_ETINIA nomes das etnias indígenas. etnia do paciente,
quando indígena. Habilitado se campo 15-Raça/Cor for igual a 5-Indígena.
17- É membro de povo ou comunidade Varchar 2(1) 1-Sim Informar se o
Campo Obrigatório POV_CT tradicional? 2-Não paciente for membro de algum
povo ou comunidade tradicional

18- Se sim, qual? Varchar 2(100) Tabela de Povos e Informar o povo ou
Campo Obrigatório- Habilitado se campo TP_POV_CT Comunidades
Tradicionais comunidade 17- É membro de povo ou comunidade tradicional?
for igual a 1- Sim tradicional 19-Escolaridade Varchar2(1) 0-Sem
escolaridade/ Nível de Campo Essencial CS_ESCOL_N Analfabeto
escolaridade do 1-Fundamental 1º ciclo (1ª a paciente. Preenchido
automaticamente com a categoria "não se aplica" quando idade 5ª série)
for menor que 7 anos 2-Fundamental 2º ciclo (6ª a Para os níveis 9ª
série) fundamental e Quando idade for maior 3- Médio (1º ao 3º ano)
médio deve ser que 7 anos, o campo não pode ser preenchido com "não se
aplica". 4-Superior considerada a 5-Não se aplica última série ou ano
9-Ignorado concluído. 20- Ocupação Varchar2(6) Tabela com código da
Ocupação Campo Essencial PAC_COCBO ou Ocupação da Classificação
profissional do PAC_DSCBO Brasileira de Ocupações paciente (CBO).

                                                                                                                               SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 5

21-Nome da mãe Varchar2(70) Nome completo da Campo Essencial NM_MAE_PAC
mãe do paciente (sem abreviações). 22-CEP Varchar2(8) CEP de residência
Campo Essencial NU_CEP do paciente. Validado a partir da tabela de CEP
dos Correios. 23-UF Varchar2(2) Tabela com código e siglas Unidade
Federativa Campo Obrigatório SG_UF das UF padronizados pelo de
residência do IBGE. paciente. Se campo 31-País for Brasil.

                                                                                                     Se preenchido o campo CEP, a UF é preenchida automaticamente pelo
                                                                                                     sistema e desabilitada para edição.

Regional de Saúde de Residência Varchar2 (6) Tabela com código e nomes
Regional de Saúde Campo Interno ID_RG_RESI OU Código (IBGE) das
Regionais de Saúde dos onde está CO_RG_RESI municípios de residência
localizado o Preenchendo o nome da regional de saúde de residência, o
código é padronizados pelo IBGE. Município de preenchido
automaticamente, e vice-versa; residência do paciente. 24-Município
Varchar2(6) Tabela com código e nome Município de Campo Obrigatório
ID_MN_RESI OU Código (IBGE) dos Municípios residência do CO_MUN_RES
padronizados pelo IBGE. paciente. Se campo 31-País for Brasil.

                                                                                                     Se preenchido o campo CEP, o Município e seu respectivo código IBGE são
                                                                                                     preenchidos automaticamente pelo sistema e desabilitados para edição.

                                                                                                     Se o CEP não for preenchido, o campo é habilitado depois de selecionada
                                                                                                     uma UF no campo 23. Nesse caso, o sistema abre tabela com os municípios
                                                                                                     da UF.

                                                                                                     Preenchendo o nome do município, o código é preenchido
                                                                                                     automaticamente, ou vice- versa.

25-Bairro Varchar2(72) Tabela com código e nome Bairro de residência
Campo Essencial NM_BAIRRO dos Bairros padronizados do paciente. pelos
Correios. Se preenchido o campo CEP, o Bairro é preenchido
automaticamente pelo sistema. 26-Logradouro (Rua, Avenida, etc.)
Varchar2(50) Tabela com código e nome Logradouro (rua, Campo Essencial
NM_LOGRADO dos logradouros avenida, quadra, padronizados pelos travessa,
etc.) do Se preenchido o campo CEP, o logradouro é preenchido
automaticamente Correios. endereço de pelo sistema. residência do

                                                                                                                             SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 6

paciente. 27-Nº Varchar2(8) Nº do logradouro Campo Essencial NU_NUMERO
(nº da casa ou do edifício). 28-Complemento (apto, casa, etc.)
Varchar2(15) Complemento do Campo Essencial NM_COMPLEM logradouro
(bloco, apto, casa, etc.). 29-(DDD) Telefone Varchar2(4) Código DDD e
Campo Essencial NU_DDD_TEL OU Varchar2(10) número de telefone NU_TELEFON
para contato do paciente. 30-Zona Varchar2(1) 1-Urbana Zona geográfica
do Campo Essencial CS_ZONA 2-Rural endereço de 3-Periurbana residência
do 9-Ignorado paciente. 31-País (se residente fora do Brasil)
Varchar2(3) Tabela com código e nome País de residência Campo
Obrigatório ID_PAIS OU dos Países. do paciente. CO_PAIS Se preenchido
CEP, ou for selecionada uma UF, o campo País é preenchido
automaticamente pelo sistema e desabilitado para edição.

                                                                                                       Se selecionado País
                                                                                                       diferente de Brasil, os campos 22 a 28 são desabilitados.

32-Trata-se de caso nosocomial Varchar2 (1) 1-Sim Caso de SRAG com Campo
Essencial NOSOCOMIAL (infecção adquirida no hospital)? 2-Não infecção
adquirida Quando o campo 32 for igual a 1, é permitido digitar data de
início dos 9-Ignorado após internação. sintomas posterior a data de
internação. 33- Paciente trabalha ou tem contato Varchar2(1) 1-Sim, aves
e/ou suínos Paciente teve Campo Essencial AVE_SUINO direto com aves,
suínos, ou outro 2-Não, nenhum contato direto ou animal? 3- Sim, outros,
qual trabalha com aves, 9-ignorado suínos ou outro animal? 33-Paciente
trabalha ou tem contato Paciente teve Campo Essencial OUT_ANIM direto
com aves, suínos/Outro animal contato direto ou Varchar2(60)
(especificar) trabalha com outro animal. Habilitado de campo 33- Contato
com outro animal = 3 (Outro). 34-Sinais e Sintomas/Febre Varchar2 (1)
1-Sim Paciente Campo Essencial FEBRE 2-Não apresentou febre? 9-Ignorado
34-Sinais e Sintomas/Tosse Varchar2 (1) 1-Sim Paciente Campo Essencial
TOSSE

                                                                                                                               SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 7

2-Não apresentou tosse? 9-Ignorado 34-Sinais e Sintomas/Dor de Garganta
Varchar2(1) 1-Sim Paciente Campo Essencial GARGANTA 2-Não apresentou dor
de 9-Ignorado garganta? 34-Sinais e Sintomas/Dispneia Varchar2(1) 1-Sim
Paciente Campo Essencial DISPNEIA 2-Não apresentou 9-Ignorado dispneia?
34-Sinais e Sintomas/Desconforto Varchar2(1) 1-Sim Paciente Campo
Essencial DESC_RESP Respiratório 2-Não apresentou 9-Ignorado desconforto
respiratório? 34-Sinais e Sintomas/Saturação Varchar2(1) 1-Sim Paciente
Campo Essencial SATURACAO O2\< 95% 2-Não apresentou 9-Ignorado saturação
O2\< 95%? 34-Sinais e Sintomas/Diarreia Varchar2(1) 1-Sim Paciente Campo
Essencial DIARREIA 2-Não apresentou 9-Ignorado diarreia? 34-Sinais e
Sintomas/Vômito Varchar2(1) 1-Sim Paciente Campo Essencial VOMITO 2-Não
apresentou 9-Ignorado vômito? 34-Sinais e Sintomas/Dor abdominal
Varchar2(1) 1-Sim Paciente Campo Essencial DOR_ABD 2-Não apresentou dor
9-Ignorado abdominal? 34-Sinais e Sintomas/Fadiga Varchar2(1) 1-Sim
Paciente Campo Essencial FADIGA 2-Não apresentou fadiga? 9-Ignorado
34-Sinais e Sintomas/Perda do Olfato Varchar2(1) 1-Sim Paciente Campo
Essencial PERD_OLFT 2-Não apresentou perda 9-Ignorado do olfato?
34-Sinais e Sintomas/Perda do Paladar Varchar2(1) 1-Sim Paciente Campo
Essencial PERD_PALA 2-Não apresentou perda 9-Ignorado do paladar?
34-Sinais e Sintomas/Outros Varchar2(1) 1-Sim Paciente Campo Essencial
OUTRO_SIN 2-Não apresentou outro(s) 9-Ignorado sintoma(s)?

                                                                                                         SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 8

34-Sinais e Sintomas/Outros Varchar2(30) Listar outros sinais Campo
Essencial OUTRO_DES (Descrição) e sintomas apresentados pelo Habilitado
se selecionado categoria 1-Sim em Sinais e Sintomas/Outros. paciente.
35-Fatores de risco Varchar2 (1) 1-Sim Paciente apresenta Campo
Essencial FATOR_RISC 2-Não algum fator de risco 9-Ignorado 35-Fatores de
risco/ Puérpera Varchar2 (1) 1-Sim Paciente é Campo Essencial PUERPERA
2-Não puérpera ou Habilitado se selecionado no campo 8- Sexo Feminino.
9-Ignorado parturiente (mulher que pariu recentemente -- até 45 dias do
parto)? 35-Fatores de risco/ Doença Varchar2 (1) 1-Sim Paciente possui
Campo Essencial CARDIOPATI Cardiovascular Crônica 2-Não Doença
9-Ignorado Cardiovascular Crônica? 35-Fatores de risco/ Doença Varchar2
(1) 1-Sim Paciente possui Campo Essencial HEMATOLOGI Hematológica
Crônica 2-Não Doença 9-Ignorado Hematológica Crônica? 35-Fatores de
risco/ Síndrome de Varchar2 (1) 1-Sim Paciente possui Campo Essencial
SIND_DOWN Down 2-Não Síndrome de 9-Ignorado Down? 35-Fatores de risco/
Doença Hepática Varchar2 (1) 1-Sim Paciente possui Campo Essencial
HEPATICA Crônica 2-Não Doença Hepática 9-Ignorado Crônica? 35-Fatores de
risco/ Asma Varchar2 (1) 1-Sim Paciente possui Campo Essencial ASMA
2-Não Asma? 9-Ignorado 35-Fatores de risco/ Diabetes mellitus Varchar2
(1) 1-Sim Paciente possui Campo Essencial DIABETES 2-Não Diabetes
mellitus? 9-Ignorado 35-Fatores de risco/ Doença Varchar2 (1) 1-Sim
Paciente possui Campo Essencial NEUROLOGIC Neurológica Crônica 2-Não
Doença 9-Ignorado Neurológica? 35-Fatores de risco/ Outra Varchar2 (1)
1-Sim Paciente possui Campo Essencial PNEUMOPATI Pneumatopatia Crônica
2-Não outra pneumopatia

                                                                                                                   SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 9

9-Ignorado crônica? 35-Fatores de risco/ Imunodeficiência Varchar2 (1)
1-Sim Paciente possui Campo Essencial IMUNODEPRE ou Imunodepressão 2-Não
Imunodeficiência 9-Ignorado ou Imunodepressão (diminuição da função do
sistema imunológico)? 35-Fatores de risco/ Doença Renal Varchar2 (1)
1-Sim Paciente possui Campo Essencial RENAL Crônica 2-Não Doença Renal
9-Ignorado Crônica? 35-Fatores de risco/ Obesidade Varchar2 (1) 1-Sim
Paciente possui Campo Essencial OBESIDADE 2-Não obesidade? 9-Ignorado
35-Fatores de risco/ Obesidade Varchar2(3) Valor do IMC Campo Essencial
OBES_IMC (Descrição IMC) (Índice de Massa Corporal) do Habilitado se
selecionado categoria 1-Sim em Fatores de risco/Obesidade. paciente
calculado pelo profissional de saúde. 35-Fatores de risco/ Tabagismo
Varchar2(1) 1-Sim Paciente é Campo Essencial TABAG 2-Não tabagista?
9-Ignorado 35-Fatores de risco/ Outros Varchar2(1) 1-Sim Paciente possui
Campo Essencial OUT_MORBI 2-Não outro(s) fator(es) 9-Ignorado de risco?
35-Fatores de risco/ Outros Varchar2(30) Listar outro(s) Campo Essencial
MORB_DESC (Descrição) fator(es) de risco do paciente. Habilitado se
selecionado categoria 1-Sim em Fatores de risco/Outros. 36- Recebeu
vacina COVID-19? Varchar(1) 1-Sim Informar se o Campo Obrigatório
VACINA_COV 2-Não paciente recebeu \*Integração com a Base Nacional de
Vacinação 9-Ignorado vacina COVID-19, após verificar a documentação /
caderneta.

37- Data 1ª dose da vacina COVID-19 Varchar(10) Date Informar a data em
Campo essencial DOSE_1_COV DD/MM/AAAA que o paciente *Integração com a
Base Nacional de Vacinação recebeu a 1ª dose da vacina COVID-19 SIVEP
Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.
Página 10  Habilitado se campo 36- Recebeu vacina COVID-19? for igual
a 1. 37- Data 2ª dose da vacina COVID-19 Varchar(10) Date Informar a
data em Campo essencial DOSE_2_COV DD/MM/AAAA que o paciente *Integração
com a Base Nacional de Vacinação recebeu a 2ª dose da vacina COVID-19
Habilitado se campo 36- Recebeu vacina COVID-19? for igual a 1. 37- Data
da dose reforço da vacina Varchar(10) Date Informar a data em Campo
essencial DOSE_REF COVID-19 DD/MM/AAAA que o paciente *Integração com a
Base Nacional de Vacinação recebeu a dose reforço Habilitado se campo
36- Recebeu vacina COVID-19? for igual a 1. 37- Data da 2ª dose reforço
da vacina Varchar(10) Date Informar a data em Campo essencial DOSE_2REF
COVID-19 DD/MM/AAAA que o paciente *Integração com a Base Nacional de
Vacinação recebeu a 2ª dose reforço Habilitado se campo 36- Recebeu
vacina COVID-19? for igual a 1. 37- Data da dose adicional da vacina
Varchar(10) Date Informar a data em Campo essencial DOSE_ADIC COVID-19
DD/MM/AAAA que o paciente *Integração com a Base Nacional de Vacinação
recebeu a dose adicional da vacina COVID-19 Habilitado se campo 36-
Recebeu vacina COVID-19? for igual a 1. 37- Data dose reforço bivalente
Varchar(10) Date Informar a data em Campo essencial DOS_RE_BI COVID-19
DD/MM/AAAA que o paciente *Integração com a Base Nacional de Vacinação
recebeu a dose reforço bivalente COVID-19 Habilitado se campo 36-
Recebeu vacina COVID-19? for igual a 1. 38- Fabricante 1ª dose da vacina
Varchar(80) Informar o Campo essencial FAB_COV1 COVID-19 fabricante da
*Integração com a Base Nacional de Vacinação vacina, que o paciente
recebeu na primeira dose Habilitado se campo 36- Recebeu vacina
COVID-19? for igual a 1. 38- Fabricante 2ª dose da vacina Varchar(80)
Informar o Campo essencial FAB_COV2 COVID-19 fabricante da *Integração
com a Base Nacional de Vacinação vacina, que o paciente recebeu na
segunda dose Habilitado se campo 36- Recebeu vacina COVID-19? for igual
a 1. 38- Fabricante dose reforço da vacina Varchar(80) Informar o Campo
essencial FAB_COVRF COVID-19 fabricante da \*Integração com a Base
Nacional de Vacinação vacina, que o

                                                                                                            SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 11

paciente recebeu na dose reforço Habilitado se campo 36- Recebeu vacina
COVID-19? for igual a 1. 38- Fabricante 2ª dose reforço da Varchar(80)
Informar o Campo essencial FAB_COVRF2 vacina COVID-19 fabricante da
*Integração com a Base Nacional de Vacinação vacina, que o paciente
recebeu na 2ª dose reforço Habilitado se campo 36- Recebeu vacina
COVID-19? for igual a 1. 38- Fabricante dose adicional da Varchar(80)
Informar o Campo essencial FAB_ADIC vacina COVID-19 fabricante da
*Integração com a Base Nacional de Vacinação vacina, que o paciente
recebeu na dose adicional Habilitado se campo 36- Recebeu vacina
COVID-19? for igual a 1. 38- Fabricante dose reforço bivalente
Varchar(80) Informar o Campo essencial FAB_RE_BI COVID-19 fabricante da
*Integração com a Base Nacional de Vacinação vacina, que o paciente
recebeu na dose reforço Habilitado se campo 36- Recebeu vacina COVID-19?
for igual a 1. bivalente 39- Lote da vacina COVID-19: Lote 1ª
Varchar(20) Informar o Lote da Campo essencial LOTE_1_COV Dose 1ª dose
da vacina *Integração com a Base Nacional de Vacinação COVID-19, que o
paciente recebeu Habilitado se campo 36- Recebeu vacina COVID-19? for
igual a 1. 39- Lote da vacina COVID-19: Lote 2ª Varchar(20) Informar o
Lote da Campo essencial LOTE_2_COV Dose 2ª dose da vacina *Integração
com a Base Nacional de Vacinação COVID-19, que o paciente recebeu
Habilitado se campo 36- Recebeu vacina COVID-19? for igual a 1. 39- Lote
da vacina COVID-19: Lote Varchar(20) Informar o Lote da Campo essencial
LOTE_REF dose reforço dose reforço da *Integração com a Base Nacional de
Vacinação vacina COVID-19, que o paciente recebeu Habilitado se campo
36- Recebeu vacina COVID-19? for igual a 1. 39- Lote da vacina COVID-19:
Lote 2ª Varchar(20) Informar o Lote da Campo essencial LOTE_REF2 dose
reforço 2ª dose reforço da \*Integração com a Base Nacional de Vacinação
vacina COVID-19, que o paciente recebeu Habilitado se campo 36- Recebeu
vacina COVID-19? for igual a 1. 39- Lote da vacina COVID-19 Dose
Varchar(20) Informar o Lote da Campo essencial LOTE_ADIC

                                                                                                SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 12

adicional dose adicional da *Integração com a Base Nacional de Vacinação
vacina COVID-19, que o paciente recebeu Habilitado se campo 36- Recebeu
vacina COVID-19? for igual a 1. 39- Lote da vacina COVID-19 Dose
Varchar(20) Informar o Lote da Campo essencial LOT_RE_BI reforço
bivalente dose reforço *Integração com a Base Nacional de Vacinação
bivalente da vacina COVID-19, que o paciente recebeu Habilitado se campo
36- Recebeu vacina COVID-19? for igual a 1. 39- Fonte dos
dados/informação sobre Varchar(1) 1- Manual Campo Interno FNT_IN_COV a
vacina COVID-19 2- Integração Número gerado automaticamente pelo
sistema.

                                                                                          Campo preenchido de acordo com a fonte dos dados/informação sobre a
                                                                                          vacina COVID-19, se foi digitada manualmente ou recuperada via
                                                                                          integração com a Base Nacional de Vacinação.

40-Recebeu vacina contra Gripe na Varchar2 (1) 1-Sim Informar se o Campo
Essencial VACINA última campanha? 2-Não paciente foi 9-Ignorado vacinado
contra gripe na última campanha, após verificar a documentação /
caderneta.

                                                                      Caso o paciente
                                                                      não tenha a
                                                                      caderneta,
                                                                      direcionar a
                                                                      pergunta para ele
                                                                      ou responsável e
                                                                      preencher o campo
                                                                      com o código
                                                                      correspondente a
                                                                      resposta.

41-Data da vacinação Date Data da última dose Campo Essencial DT_UT_DOSE
DD/MM/AAAA de vacina contra gripe que o Habilitado se campo paciente
tomou. 40-Recebeu vacina contra Gripe na última campanha? for igual a 1.

                                                                                          Data deve ser <= a data da digitação (data atual).
                                                                                                                 SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 13

Se \< 6 meses: a mãe recebeu a vacina? Varchar2 (1) 1-Sim Se paciente \<
6 Campo Essencial MAE_VAC 2-Não meses, a mãe 9-Ignorado recebeu vacina?
Habilitar campo

                                                                                                    Se a Idade do caso for < 6 meses.

Se sim, data Date Se a mãe recebeu Campo Essencial DT_VAC_MAE DD/MM/AAAA
vacina, qual a data? Habilitado se campo Se \< 6 meses: a mãe recebeu a
vacina for igual a 1.

                                                                                                    Data deve ser <= a data da digitação (data atual).

Se \< 6 meses: a mãe amamenta a Varchar2 (1) 1-Sim Se paciente \< 6
Campo Essencial M_AMAMENTA criança? 2-Não meses, a mãe 9-Ignorado
amamenta a Habilitar campo se criança? Se a Idade do caso for \< 6
meses. Se \>= 6 meses e \<= 8 anos: Data da Date Se \>= 6 meses e \<=
Campo Essencial DT_DOSEUNI dose única 1/1 DD/MM/AAAA 8 anos, data da
dose única para Habilitar campo crianças vacinadas em campanhas de Se a
Idade do caso for \>= 6 meses e \<= 8 anos anos anteriores Se \>= 6
meses e \<= 8 anos: Data da 1ª Date Se \>= 6 meses e \<= Campo Essencial
DT_1_DOSE dose DD/MM/AAAA 8 anos, data da 1ª dose para crianças
Habilitar campo vacinadas pela primeira vez Se a Idade do caso for \>= 6
meses e \<= 8 anos Se \>= 6 meses e \<= 8 anos: Data da 2ª Date Se \>= 6
meses e \<= Campo Essencial DT_2_DOSE dose DD/MM/AAAA 8 anos data da 2ª
dose para crianças Habilitar campo vacinadas pela primeira vez Se a
Idade do caso for \>= 6 meses e \<= 8 anos 42-Usou antiviral para gripe?
Varchar2 (1) 1-Sim Fez uso de antiviral Campo Essencial ANTIVIRAL 2-Não
para tratamento da 9-Ignorado doença? 43-Qual antiviral? Varchar2 (1) 1-
Oseltamivir Qual antiviral Campo Essencial TP_ANTIVIR 2- Zanamivir
utilizado? Habilitado se campo 42-Usou antiviral para gripe? for igual
a 1. 3- Outro, especifique Qual antiviral /Outro, especifique
Varchar2(30) Se o antiviral Campo Essencial OUT_ANTIV

                                                                                                                           SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 14

utilizado não foi Oseltamivir ou Habilitado se campo 40- Qual antiviral?
for igual a 3. Zanamivir, informar qual antiviral foi utilizado. 44-Data
do início do tratamento Date Data em que foi Campo Essencial DT_ANTIVIR
DD/MM/AAAA iniciado o tratamento com o Habilitado se campo 42-Usou
antiviral para gripe? for igual a 1. antiviral. Data deve ser \<= a data
da digitação (data atual). 45- Recebeu tratamento antiviral para
Varchar2(1 1-Sim Fez uso de antiviral Campo Essencial TRAT_COV covid-19?
2-Não para tratamento de 9-Ignorado covid-19? 46- Qual antiviral?
Varchar2(1) 1-Nirmatrevir/ritonavir Se foi feito uso de Habilitado se
campo 45-Recebeu tratamento antiviral para covid-19? for TIPO_TRAT
(Paxlovid ®) antiviral para igual a 1. 2- Molnupiravir(Lagevrio®)
tratamento de 3- Baricitinibe (Olumiant®) covid-19, informar 4- Outro,
especifique qual, conforme relação disponível. Qual antiviral /Outro,
especifique Varchar2(30) Se o antiviral Campo Essencial OUT_TRAT
utilizado não foi, 1- Nirmatrevir/ritonav Habilitado se campo 46- Qual
antiviral? for igual a 4. ir (Paxlovid ®) 2- Molnupiravir (Lagevrio®) 3-
Baricitinibe (Olumiant®), informar qual antiviral foi utilizado. 47-
Data do início do tratamento Date Data em que foi Campo Essencial
DT_TRT_COV DD/MM/AAAA iniciado o Habilitado se campo 45-Recebeu
tratamento antiviral para covid-19? for tratamento com o igual a 1.
antiviral, para Data deve ser \<= a data da digitação (data atual).
tratamento de covid-19. 48-Houve internação? Varchar2(1) 1-Sim O
paciente foi Campo Essencial HOSPITAL 2-Não internado? 9-Ignorado Caso o
campo não seja igual a 1 -- Sim o sistema emitirá um aviso indicando que
não atende a definição de caso.

                                                                                                                                  SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 15

49-Data da internação por SRAG Date Data em que o Campo Obrigatório
DT_INTERNA DD/MM/AAAA paciente foi hospitalizado. Data deve ser maior ou
igual a 2- Data de 1ºs sintomas e menor ou igual a data da digitação
(atual).

50-UF de internação Varchar2(2) Tabela com código e siglas Unidade
Federativa Campo Essencial SG_UF_INTE das UF padronizados pelo de
internação do IBGE. paciente. Habilitado se campo 48-Houve internação?
for igual a 1 Regional de Saúde de Internação Varchar2 (6) Tabela com
código e nomes Regional de Saúde Campo Interno ID_RG_INTE OU Código
(IBGE) das Regionais de Saúde dos onde está CO_RG_INTE municípios de
internação localizado o Preenchendo o nome da regional de saúde de
internação, o código é padronizados pelo IBGE. Município de preenchido
automaticamente, e vice-versa. internação do paciente. 51-Município de
internação/ Varchar2 (20) Tabela com código e nomes Município onde Campo
Essencial ID_MN_INTE OU Código(IBGE) dos Municípios está localizado a
CO_MU_INTE padronizados pelo IBGE. Unidade de Saúde Habilitado se campo
48-Houve internação? for igual a 1 onde o paciente internou. 52-Unidade
de Saúde de internação/ Varchar2(20) Tabela com códigos CNES e Unidade
que Campo Essencial ID_UN_INTE OU Código CNES nomes das Unidades de
realizou a CO_UN_INTE Saúde. internação do Habilitado se campo 48-Houve
internação? for igual a 1 paciente. 53-Internado em UTI? Varchar2(1)
1-Sim O paciente foi Campo Essencial UTI 2-Não internado em UTI?
9-Ignorado 54-Data da entrada na UTI Date Data de entrada do Campo
Essencial DT_ENTUTI DD/MM/AAAA paciente na unidade de Terapia Habilitado
se campo 53-Internado em UTI? for igual a 1. intensiva (UTI). Data deve
ser maior ou igual a 2-Data de 1ºs sintomas da SRAG e menor ou igual a
data da digitação (atual). 55-Data da saída da UTI Date Data em que o
Campo Essencial DT_SAIDUTI DD/MM/AAAA paciente saiu da Unidade de
Terapia Habilitado se campo 53-Internado em UTI? for igual a 1.
intensiva (UTI). Data deve ser maior ou igual a 54-Data da entrada na
UTI e menor ou igual a data da digitação (atual).

                                                                                                                                SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 16

56-Uso de suporte ventilatório? Varchar2(1) 1-Sim, invasivo O paciente
fez uso Campo Essencial SUPORT_VEN 2-Sim, não invasivo de suporte 3-Não
ventilatório? 9-Ignorado 57- Raio X de Tórax Varchar2(1) 1-Normal
Informar resultado Campo Essencial RAIOX_RES 2-Infiltrado intersticial
de Raio X de Tórax. 3-Consolidação 4-Misto 5-Outro 6-Não realizado
9-Ignorado Raio X de Tórax/ Outro (especificar) Informar o RAIOX_OUT
resultado do RX de Campo Essencial Varchar2(30) tórax se selecionado a
Habilitado de campo 57- Raio X de Tórax = 5 (Outro). opção 5-Outro.
58-Data do Raio X Data Se realizou RX de Campo Essencial DT_RAIOX
DD/MM/AAAA Tórax, especificar a data do exame. Habilitado se campo 57-
Raio X de Tórax for igual a 1, 2, 3, 4 ou 5. 59- Aspecto Tomografia
Number(3) 1-Tipico covid-19 Informar o TOMO_RES 2- Indeterminado
covid-19 resultado da 3- Atípico covid-19 tomografia. Campo Essencial 4-
Negativo para Pneumonia 5- Outro 6-Não realizado 9-Ignorado Aspecto
Tomografia/Outro Varchar2(100) Informar o TOMO_OUT (especificar)
resultado da Campo Essencial tomografia se Habilitado de campo 53-
Aspecto Tomografia = 5 (Outro selecionado a opção 5-Outro 60- Data da
Tomografia Data Se realizou DT_TOMO DD/MM/AAAA tomografia, Campo
Essencial especificar a data Habilitado se campo 59- Aspecto Tomografia
for igual a 1, 2, 3, 4 ou 5. do exame. 61-Coletou amostra? Varchar2 (1)
1-Sim Foi realizado coleta Campo Essencial AMOSTRA 2-Não de amostra para
9-Ignorado realização de teste diagnóstico?

                                                                                                                                SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 17

62-Data da Coleta Date Data da coleta da Campo Essencial DT_COLETA
DD/MM/AAAA amostra para realização do teste Habilitado de campo
55-Coletou amostra? = 1. diagnóstico. Data deve ser maior ou igual a
2-Data de 1ºs sintomas e menor ou igual a data da digitação (atual).
63-Tipo de amostra Varchar2(30) 1-Secreção de Naso- Tipo da amostra
Campo Essencial TP_AMOSTRA orofaringe clínica coletada 2-Lavado
Broco-alveolar para o teste Habilitado de campo 61-Coletou amostra? = 1.
3-Tecido post-mortem diagnóstico. 4-Outra, qual? 5-LCR 9-Ignorado Tipo
de amostra/Outra Varchar2(30) Descrição do tipo Campo Essencial
OUT_AMOST da amostra clínica, caso diferente das Campo habilitado se
selecionado categoria 4-Outra, qual em Tipo de listadas nas amostra.
categorias do campo. 64-Nº da Requisição do GAL Número da Campo
Essencial REQUI_GAL requisição de exames gerado pelo sistema GAL. 65-
Tipo do Teste antigênico Number(3) 1-Imunofluorescência (IF) Tipo do
teste Campo Essencial 2- Teste rápido antigênico antigênico que foi
TP_TES_AN realizado.

66- Data do resultado teste Data Data do resultado Campo Essencial
DT_RES_AN Antigênico DD/MM/AAAA do teste antigênico. Data deve ser maior
ou igual a 62- Data da Coleta 67- Resultado do Teste Antigênico
Varchar2(1) 1-positivo Resultado do Teste Campo Essencial RES_AN
2-Negativo Antigênico 3- Inconclusivo Este campo virá marcado com
5-Aguardando Resultado e estará habilitado se 4-Não realizado o campo
61-Coletou amostra? = 1 5-Aguardando resultado 9-Ignorado 68-Laboratório
que realizou o Teste Varchar2(70) Nomes dos Laboratórios Laboratório
Campo Essencial LAB_AN antigênico cadastrados no sistema responsável
pela liberação do Habilitado se campo 67- Resultado do teste antigênico:
estiver selecionado resultado do teste como 1-Positivo, 2- Negativo, 3-
Inconclusivo ou 5- Aguardando resultado.

                                                                                                                              SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 18

antigênico. Preenchendo o nome do Laboratório, o código é preenchido
automaticamente, ou vice-versa. 68-Laboratório que realizou o Teste
Varchar2(7) Tabela com códigos CNES Campo Essencial CO_LAB_AN antigênico
69-Agente etiológico -- Teste Varchar2(1) 1-Sim Resultado do Teste Campo
Essencial POS_AN_FLU Antigênico. 2-Não Antigênico que foi Positivo para
Influenza? 9-Ignorado positivo para Influenza 69-Agente etiológico --
Teste Varchar2(1) 1-Influenza A Resultado do Teste Campo Essencial
TP_FLU_AN Antigênico. 2-Influenza B Antigênico, para o Se sim, qual
Influenza? tipo de Influenza. Habilitado se campo 69-Agente etiológico
-- Teste Antigênico: Positivo para Influenza? = 1. 69-Agente etiológico
-- Teste Varchar2 (1) 1-Sim Resultado do Teste Campo Essencial
POS_AN_OUT Antigênico. 2-Não Antigênico, que foi 9-Ignorado positivo
para outro Positivo para outros vírus? vírus respiratório. 69-Agente
etiológico -- Teste Varchar2(1) 1-marcado pelo usuário Resultado do
Teste Campo Essencial AN_SARS2 Antigênico. Vazio - não marcado
Antigênico, para SARS-CoV-2 SARS-CoV-2. Habilitado se campo 69-Agente
etiológico, Teste Antigênico. Positivo para outros vírus? = 1. 69-Agente
etiológico -- Teste Varchar2(1) 1-marcado pelo usuário Resultado do
Teste Campo Essencial AN_VSR Antigênico. Vazio - não marcado Antigênico,
para VSR VSR. Habilitado se campo 69-Agente etiológico, Teste
Antigênico. Positivo para outros vírus? = 1. 69-Agente etiológico --
Teste Varchar2 (1) 1-marcado pelo usuário Resultado do Teste Campo
Essencial AN_PARA1 Antigênico. Vazio - não marcado Antigênico, para
Parainfluenza 1 Parainfluenza 1. Habilitado se campo 69-Agente
etiológico, Teste Antigênico. Positivo para outros vírus? = 1. 69-Agente
etiológico -- Teste Varchar2 (1) 1-marcado pelo usuário Resultado do
Teste Campo Essencial AN_PARA2 Antigênico. Vazio - não marcado
Antigênico. Habilitado se campo 69-Agente etiológico, Teste Antigênico
Parainfluenza 2 Parainfluenza 2. Positivo para outros vírus? = 1.
69-Agente etiológico -- Teste Varchar2(1) 1-marcado pelo usuário
Resultado do Teste Campo Essencial AN_PARA3 Antigênico. Vazio - não
marcado Antigênico. Parainfluenza 3 Parainfluenza 3. Habilitado se campo
69-Agente etiológico, Teste Antigênico. Positivo para outros vírus? = 1.
69-Agente etiológico -- Teste Varchar2(1) 1-marcado pelo usuário
Resultado do Teste Campo Essencial AN_ADENO Antigênico. Vazio - não
marcado Antigênico. Adenovírus Adenovírus. Habilitado se campo 69-Agente
etiológico, Teste Antigênico.

                                                                                                                              SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 19

Positivo para outros vírus? = 1. 69- Agente etiológico -- Teste Varchar2
(1) 1-marcado pelo usuário Resultado do Teste Campo Essencial AN_OUTRO
Antigênico. Vazio - não marcado Antigênico. Outro vírus respiratório
Outro vírus Habilitado se campo 69-Agente etiológico, Teste Antigênico.
respiratório. Positivo para outros vírus? = 1. 69- Agente etiológico --
Teste Varchar2(30) Nome do outro Campo Essencial DS_AN_OUT Antigênico.
vírus respiratório Outro vírus respiratório (Descrição) identificado
pelo Habilitado se campo 69-Agente etiológico, Teste Antigênico. Teste
Antigênico. Positivo para outros vírus? = 1.

70-Resultado da RT-PCR/outro Varchar2 (1) 1-Detectável Resultado do
teste Campo Essencial PCR_RESUL método por Biologia Molecular 2-Não
Detectável de RT-PCR/outro 3-Inconclusivo método por Este campo virá
marcado com 5-Aguardando Resultado e estará habilitado se 4-Não
Realizado Biologia Molecular. o campo 61-Coletou amostra? = 1.
5-Aguardando Resultado 9-Ignorado 71-Data do Resultado RT-PCR/outro Date
Data do Resultado Campo Essencial DT_PCR método por Biologia Molecular
DD/MM/AAAA RT-PCR/outro método por Campo habilitado se selecionado
categoria 1-Detectável, 2-Não Detectável Biologia Molecular ou
3-Inconclusivo em Resultado da RT-PCR/outro método por Biologia
Molecular.

                                                                                                        Data deve ser >= a data da coleta- campo 62.

72- Agente etiológico -- RT-PCR/outro Varchar2 (1) 1-Sim Resultado da
RT- Campo Essencial POS_PCRFLU método por Biologia Molecular: 2-Não PCR
foi positivo Positivo para Influenza? 9-Ignorado para Influenza 72-
Agente etiológico -- RT-PCR/outro Varchar2(1) 1-Influenza A Resultado
Campo Essencial TP_FLU_PCR método por Biologia Molecular: 2-Influenza B
diagnóstico do RT- Se sim, qual Influenza? PCR para o tipo de Habilitado
se campo 72-Agente etiológico -- RT_PCR/outro método por Influenza.
Biologia Molecular: Positivo para Influenza? = 1. 72- Agente etiológico
-- RT-PCR/outro Varchar2(1) 1-Influenza A(H1N1)pdm09 Subtipo para Campo
Essencial PCR_FLUASU método por Biologia Molecular: 2-Influenza A (H3N2)
Influenza A. Se Influenza A, qual subtipo? 3-Influenza A não subtipado
Habilitado se campo 72-Agente etiológico -- RT_PCR/outro método por
4-Influenza A não subtipável Biologia Molecular: Se sim, qual Influenza?
= 1. 5-Inconclusivo 6-Outro, especifique: 72- Agente etiológico --
RT-PCR/outro Varchar2 (30) Outro subtipo para Campo Essencial FLUASU_OUT
método por Biologia Molecular: Influenza A. Se Influenza A, qual
subtipo? Outro, Habilitado se campo 72-Agente etiológico -- RT-PCR/outro
método por

                                                                                                                               SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 20

especifique: Biologia Molecular: Se Influenza A, qual subtipo? = 6. 72-
Agente etiológico -- RT-PCR/outro Varchar2(1) 1-Victoria Linhagem para
Campo Essencial PCR_FLUBLI método por Biologia Molecular: 2-Yamagatha
Influenza B. Se Influenza B, qual linhagem? 3-Não realizado Habilitado
se campo 72-Agente etiológico -- RT_PCR/outro método por 4-Inconclusivo
Biologia Molecular: Se sim, qual Influenza? = 2. 5-Outro, especifique:
72- Agente etiológico -- RT-PCR/outro Varchar2 (30) Outra linhagem Campo
Essencial FLUBLI_OUT método por Biologia Molecular: para Influenza B. Se
Influenza B, qual linhagem? Outro, Habilitado se 72- Agente etiológico
-- RT-PCR/outro método por Biologia especifique: Molecular: Se Influenza
B, qual linhagem? = 5. 72- Agente etiológico -- RT-PCR/outro Varchar2
(1) 1-Sim Resultado da RT- Campo Essencial POS_PCROUT método por
Biologia Molecular: 2-Não PCR foi positivo Positivo para outros vírus?
9-Ignorado para outro vírus respiratório 72- Agente etiológico --
RT-PCR/outro Varchar2 (1) 1-marcado pelo usuário Resultado Campo
Essencial PCR\_ SARS2 método por Biologia Molecular: Vazio - não marcado
diagnóstico do RT- SARS-CoV-2 PCR para (SARS-CoV- Habilitado se campo
72- Agente etiológico -- RT-PCR/outro método por 2). Biologia Molecular:
Positivo para outros vírus? = 1. 72- Agente etiológico -- RT-PCR/outro
Varchar2 (1) 1-marcado pelo usuário Resultado Campo Essencial PCR_VSR
método por Biologia Molecular: Vazio - não marcado diagnóstico do RT-
VSR PCR para (VSR). Habilitado se campo 72- Agente etiológico --
RT-PCR/outro método por Biologia Molecular: Positivo para outros vírus?
= 1 72- Agente etiológico -- RT-PCR/outro Varchar2 (1) 1-marcado pelo
usuário Resultado Campo Essencial PCR_PARA1 método por Biologia
Molecular: Vazio - não marcado diagnóstico do RT- Parainfluenza 1 PCR
para Habilitado se campo 72- Agente etiológico -- RT-PCR/outro método
por Parainfluenza 1. Biologia Molecular: Positivo para outros vírus? = 1
72- Agente etiológico -- RT-PCR/outro Varchar2 (1) 1-marcado pelo
usuário Resultado Campo Essencial PCR_PARA2 método por Biologia
Molecular: Vazio - não marcado diagnóstico do RT- Parainfluenza 2 PCR
para Habilitado se campo 72- Agente etiológico -- RT-PCR/outro método
por Parainfluenza 2. Biologia Molecular: Positivo para outros vírus? = 1
72- Agente etiológico -- RT-PCR/outro Varchar2 (1) 1-marcado pelo
usuário Resultado Campo Essencial PCR_PARA3 método por Biologia
Molecular: Vazio - não marcado diagnóstico do RT- Parainfluenza 3 PCR
para Habilitado se campo 72- Agente etiológico -- RT-PCR/outro método
por

                                                                                                                            SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 21

Parainfluenza 3. Biologia Molecular: Positivo para outros vírus? = 1 72-
Agente etiológico -- RT-PCR/outro Varchar2 (1) 1-marcado pelo usuário
Resultado Campo Essencial PCR_PARA4 método por Biologia Molecular:
Vazio - não marcado diagnóstico do RT- Parainfluenza 4 PCR para
Habilitado se campo 72- Agente etiológico -- RT-PCR/outro método por
Parainfluenza 4. Biologia Molecular: Positivo para outros vírus? = 1 72-
Agente etiológico -- RT-PCR/outro Varchar2 (1) 1-marcado pelo usuário
Resultado Campo Essencial PCR_ADENO método por Biologia Molecular:
Vazio - não marcado diagnóstico do RT- Adenovírus PCR para Habilitado se
campo 72- Agente etiológico -- RT-PCR/outro método por Adenovírus.
Biologia Molecular: Positivo para outros vírus? = 1 72- Agente
etiológico -- RT-PCR/outro Varchar2 (1) 1-marcado pelo usuário Resultado
Campo Essencial PCR_METAP método por Biologia Molecular: Vazio - não
marcado diagnóstico do RT- Metapneumovírus PCR para Habilitado se campo
72- Agente etiológico -- RT-PCR/outro método por Metapneumovírus.
Biologia Molecular: Positivo para outros vírus? = 1 72- Agente
etiológico -- RT-PCR/outro Varchar2 (1) 1-marcado pelo usuário Resultado
Campo Essencial PCR_BOCA método por Biologia Molecular: Vazio - não
marcado diagnóstico do RT- Bocavírus PCR para Bocavírus. Habilitado se
campo 72- Agente etiológico -- RT-PCR/outro método por Biologia
Molecular: Positivo para outros vírus? = 1 72- Agente etiológico --
RT-PCR/outro Varchar2 (1) 1-marcado pelo usuário Resultado Campo
Essencial PCR_RINO método por Biologia Molecular: Vazio - não marcado
diagnóstico do RT- Rinovírus PCR para Rinovírus. Habilitado se campo 72-
Agente etiológico -- RT-PCR/outro método por Biologia Molecular:
Positivo para outros vírus? = 1 72- Agente etiológico -- RT-PCR/outro
Varchar2 (1) 1-marcado pelo usuário Resultado Campo Essencial PCR_OUTRO
método por Biologia Molecular: Vazio - não marcado diagnóstico do RT-
Outro vírus respiratório, especifique: PCR para Outro Habilitado se
campo 72- Agente etiológico -- RT-PCR/outro método por vírus
respiratório. Biologia Molecular: Positivo para outros vírus? = 1 72-
Agente etiológico -- RT-PCR/outro Varchar2 (30) Nome do outro Campo
Essencial DS_PCR_OUT método por Biologia Molecular: vírus respiratório
Outro vírus respiratório (Descrição) identificado pelo Habilitado se 72-
Agente etiológico -- RT-PCR/outro método por Biologia RT-PCR. Molecular:
Outro vírus respiratório, especifique: 73-Laboratório que realizou RT-
Varchar2 (7) Tabela com códigos CNES e Laboratório Campo Essencial
LAB_PCR OU PCR/outro método por Biologia nomes dos Laboratórios
responsável pela CO_LAB_PCR

                                                                                                                              SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 22

Molecular cadastrados no sistema. liberação do Habilitado se selecionado
categoria 1-Detectável, 2-Não Detectável ou 3- Código (CNES) resultado
do teste Inconclusivo em 70-Resultado da RT-PCR/outro método por
Biologia diagnóstico (RT- Molecular. PCR) da amostra do paciente.
Preenchendo o nome do Laboratório, o código é preenchido
automaticamente, ou vice-versa. 74- Tipo de Amostra Sorológica para
Number(3) 1- Sangue/plasma/soro Tipo de amostra Campo Essencial
TP_AM_SOR SARS-Cov-2 2-Outra, qual? sorológica que foi 9-Ignorado
coletada. Tipo de Amostra Sorológica para SARS- Descrição do tipo Campo
Essencial SOR_OUT Cov-2/Outra, qual? da amostra clínica, caso diferente
das Campo habilitado se selecionado categoria 2-Outra, qual? listadas na
em Tipo de Amostra Sorológica. categoria um (1) do campo.

75- Data da coleta Data Data da coleta do Campo Essencial DT_CO_SOR
DD/MM/AAAA material para diagnóstico por Habilitado de campo 61-Coletou
amostra? = 1. Sorologia. Data deve ser maior ou igual a 2-Data de 1ºs
sintomas e menor ou igual a data da digitação (atual). 76- Tipo de
Sorologia para SARS-Cov-2 Number(3) 1-Teste rápido Tipo do Teste Campo
Essencial TP_SOR 2-Elisa Sorológico que foi 3- Quimiluminescência
realizado 4- Outro, qual 76- Tipo de Sorologia para SARS-Cov-2 Varchar
2(100) Descrição do tipo Campo Essencial OUT_SOR de Teste Sorológico
Campo habilitado se selecionado categoria 4-Outro, qual? em Tipo de
Sorologia. 76- Tipo de Sorologia para SARS-Cov- Varchar 2(100) Outro
tipo de SOR_OUT 2/Outro, qual? amostra Sorológica 76- Resultado do Teste
Sorológico para Varchar2(1) IgG Resultado da Campo Essencial RES_IGG
SARS-CoV-2: Sorologia para SARS-CoV-2 76- Resultado do Teste Sorológico
para Varchar2(1) IgM Resultado da Campo Essencial RES_IGM SARS-CoV-2:
Sorologia para SARS-CoV-2 76- Resultado do Teste Sorológico para
Varchar2(1) IgA Resultado da Campo Essencial RES_IGA SARS-CoV-2:
Sorologia para SIVEP Gripe- Sistema de Informação da Vigilância
Epidemiológica da Gripe. Página 23  SARS-CoV-2 77- Data do Resultado
Date Data do Resultado Campo Essencial DT_RES DD/MM/AAAA do Teste
Sorológico Data deve ser maior ou igual a 75- Data da Coleta

78- Faz parte de uma cadeia de surto Varchar2(1) 1-Sim O caso faz parte
de Campo essencial SURTO_SG de SG? 2-Não uma cadeia de 9-Ignorado surto
de SG. 79- É um caso de co-detecção? Varchar2(1) 1-Sim O caso trata-se
de Campo essencial CO-DETEC 2-Não co-detecção, onde 9-Ignorado foram
identificados dois tipos de vírus ao mesmo tempo. 80-Classificação final
do caso Varchar2(1) 1-SRAG por influenza Diagnóstico final do Campo
Obrigatório CLASSI_FIN 2-SRAG por outro vírus caso. respiratório 3-SRAG
por outro agente etiológico, qual: 4-SRAG não especificado Se tiver
resultados 5-SRAG por covid-19 divergentes entre as metodologias
laboratoriais, priorizar o resultado do RT- PCR. 80-Classificação final
do caso Varchar2(30) Descrição de qual Campo Obrigatório CLASSI_OUT
3-SRAG por outro agente etiológico, outro agente qual: etiológico foi Se
campo 80-Classificação final do caso = 3. identificado Habilitado se
campo 80-Classificação final do caso = 3. 81--Critério de Encerramento
Varchar2(1) 1. Laboratorial Indicar qual o Campo Essencial CRITERIO 2.
Clínico Epidemiológico critério de OBS. Os critérios de encerramento: 3.
clínico e 4. clínico-imagem , não são 3. Clínico confirmação. mais
considerados para o encerramento de SRAG por covid-19 desde 4. Clínico
Imagem 31/10/2022. ATENÇÃO: O critério de encerramento clínico-imagem,
não é utilizado para encerramento de SRAG por Influenza, por outros
vírus respiratórios, por outro agente etiológico e por SRAG não
especificado. 82--Evolução do caso Varchar2(1) 1-Cura Evolução do caso
Campo Essencial EVOLUCAO 2-Óbito 3- Óbito por outras causas 9-Ignorado
SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da
Gripe. Página 24 83--Data da alta ou óbito Date Data da alta ou Campo
Essencial DT_EVOLUCA DD/MM/AAAA óbito Data da alta ou do óbito deve ser
\> ou = a data dos primeiros sintomas e \<= a data da digitação (atual).

                                                                           Habilitado se campo 82- Evolução do caso = 1 ou 2.

84-Data do Encerramento Date Data do Campo Obrigatório DT_ENCERRA
DD/MM/AAAA encerramento do caso. Se o campo 80- Classificação final do
caso estiver preenchido.

                                                                           Data do encerramento deve ser > ou = a data do preenchimento.

                                                                           Data do encerramento deve ser < ou = a data da digitação (atual).

85- Número D.O Número da Campo Essencial NU_DO Declaração de Óbito
Habilitado se o campo 80- Evolução do caso = 2 ou 3

86-Observações Varchar2(999) Outras observações Campo Opcional OBSERVA
sobre o paciente consideradas pertinentes. 87-Profissional de Saúde
Responsável Varchar2(60) Nome completo do Campo Essencial NOME_PROF
profissional de saúde (sem abreviações) responsável pela notificação.
88-Registro Conselho/Matrícula Varchar2(15) Número do Campo Essencial
REG_PROF conselho ou matrícula do profissional de saúde responsável pela
notificação (Ex: CRM/RJ 1234) Data da digitação Date Data de inclusão do
Campo Interno DT_DIGITA DD/MM/AAAA registro no sistema. Preenchido
automaticamente pelo sistema com a data da digitação da ficha. Não é a
data de preenchimento da ficha manualmente e sim a data em que é
digitado no sistema. Não é atualizada se houver alterações posteriores
de dados.

                                                                                                 SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 25

89- Designação da variante (OMS) Varchar2(1) 1- Ômicron Denominação da
Campo Essencial VG_OMS 2- Delta variante 3- Alfa identificada de 4- Beta
acordo com a 5- Gama designação da 6- Recombinante (Exemplos:
Organização XE, XF, XQ, XS...) Mundial da Saúde 7- Outra, especifique:
(OMS). 89- Designação da variante (OMS): Varchar2 (30) Denominação de
Campo Essencial VG_OMSOUT Outra, especifique: novas variantes, que ainda
não constam na relação disponível.

90- Linhagem da variante Varchar2 (15) Especificação da Campo Essencial
VG_LIN linhagem Se o campo 89- Designação da variante (OMS) for
preenchido, esse campo identificada no passa a ser de preenchimento
obrigatório. resultado do sequenciamento genômico. 91- Método
laboratorial mais recente Varchar2(1) 1- Sequenciamento Metodologia
Campo Essencial VG_MET genômico completo laboratorial que foi 2-
Sequenciamento realizada mais genômico parcial recente 3. RT-PCR em
tempo real de inferência 4-Outro, especifique 91- Método laboratorial
mais recente: Varchar2 (30) Habilitado se campo 91- Método laboratorial
mais recente = 4. VG_METOUT Outro, especifique

92- Nome do laboratório Varchar2(70) Laboratório Campo Essencial VG_LAB
responsável pela liberação do resultado do sequenciamento da amostra do
paciente.

                                                                                                                              SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 26

93- Código (CNES) do laboratório Varchar2 (7) Código Cadastro Campo
Essencial VG_CODLAB Nacional de Estabelecimento de Saúde (CNES).

94- Data do resultado Date Campo Essencial VG_DTRES DD/MM/AAAA

95- Encerramento do caso (para VOC, Varchar2(1) 1- Confirmado por
Encerramento do Campo Essencial VG_ENC VOI ou VUM) Sequenciamento
genômico caso conforme Se o campo 89- Designação da variante (OMS) for
preenchido, esse campo completo orientações na passa a ser de
preenchimento obrigatório. 2- Provável por Nota Técnica (NT)
Sequenciamento genômico 1.129/2021- parcial) CGPNI/DEIDT/SVS/ 3-
Sugestivo por RT-PCR de MS. inferência 4- Sugestivo por vínculo
epidemiológico 5- Descartado 96- Possível caso de reinfecção por
Varchar2(1) 1-Sim Possível caso de Campo Essencial VG_REINF covid-19?
2-Não reinfecção 9-Ignorado (paciente com registro anterior positivo
para covid- 19, com intervalo maior ou igual a 90 dias). 97-
Profissional responsável pelo Varchar2 (60) Nome completo do Campo
Essencial VG_PROF preenchimento profissional de saúde (sem abreviações)
responsável pelo preenchimento das informações de Vigilância Genômica
Epidemiológica e Reinfecção.

                                                                                                                            SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 27

98- Estabelecimento responsável pelo Varchar2 (60) Estabelecimento Campo
Essencial VG_EST preenchimento responsável pelo Se o campo 89-
Designação da variante (OMS) for preenchido, esse campo preenchimento da
passa a ser de preenchimento obrigatório. informação.

98- Código (CNES) do Estabelecimento Varchar2 (7) Código Cadastro Campo
Essencial VG_CODDEST responsável pelo preenchimento Nacional de
Estabelecimento de Saúde (CNES).

                                                                                               SIVEP Gripe- Sistema de Informação da Vigilância Epidemiológica da Gripe.   Página 28
