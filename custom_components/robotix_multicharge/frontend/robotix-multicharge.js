/* Robotix MultiCharge native Home Assistant card: one backend, five honest views. */
let mcLanguage="en";
const MC_TEXT={"nl":{"Overview":"Overzicht","Charging Plan":"Laadplan","Chargeable Assets":"Voertuigen","Chargers":"Laadpalen","Settings":"Instellingen","Charging plan":"Laadplan","Charging overview":"Laadoverzicht","Refresh":"Vernieuwen","Today":"Vandaag","Tomorrow":"Morgen","All chargers":"Alle laadpalen","Show labels":"Toon","Color by":"Kleur per","Indicative forecasting":"Prognose","Vehicle":"Voertuig","Charger":"Laadpaal","Vehicle + Charger":"Voertuig + laadpaal","Show (not reserved)":"Tonen","Hide":"Verbergen","Proposed":"Voorgesteld","Accepted":"Bevestigd","Measured":"Gemeten","Indicative":"Indicatief","No vehicle selected":"Geen voertuig","Connected":"Aangesloten","Disconnected":"Niet aangesloten","Connection unknown":"Aansluiting onbekend","Vehicle unknown":"Voertuig onbekend","Unavailable":"Niet beschikbaar","Unknown":"Onbekend","Not set":"Niet ingesteld","Not assigned":"Niet toegewezen","Plan color":"Plankleur","Plan labels":"Planlabels","Active chargers":"Actieve laadpalen","Actual power":"Werkelijk vermogen","Current price":"Huidig tarief","Charging strategy":"Laadmodus","Charging site":"Laadlocatie","Sources & bindings":"Bronnen","Safety & limits":"Veiligheid en limieten","Integrations":"Integraties","Advanced & YAML":"Geavanceerd","Readiness":"Gereedheid","Battery":"Batterij","Target":"Doel","Ready By":"Klaar om","Priority":"Prioriteit","Duration":"Duur","Requested energy":"Gevraagde energie","Charging intention":"Laadbehoefte","Charging priority":"Prioriteit","Connection":"Aansluiting","Selected vehicle":"Gekozen voertuig","Assigned asset":"Gekozen voertuig","Actual current":"Gemeten stroom","Power":"Vermogen","Source state":"Bronstatus","Status":"Status","Start charging":"Start laden","Stop charging":"Stop laden","Details":"Details","Hide details":"Sluiten","Edit":"Wijzigen","Saved":"Opgeslagen","Pending":"In behandeling","Rejected":"Geweigerd","Next planned session":"Volgende laadsessie","Next action":"Volgende stap","No active qualified vehicle plan":"Geen actieve planning","No qualified slots for this day.":"Geen laadmomenten","No vehicles":"Geen voertuigen","No charging points":"Geen laadpalen","Loading":"Laden","Error":"Fout","No data":"Geen gegevens","No connection":"Niet aangesloten","Not ready":"Niet gereed","Waiting":"Wachten","Forecast":"Prognose","If connected now":"Bij nu aansluiten","Expected":"Verwacht","Not reserved":"Niet gereserveerd","Measured power unavailable":"Geen meetgegevens","Vehicle plan":"Voertuigplan","Charger plan":"Laadpaalplan","No forecast":"Geen prognose","No vehicle":"Geen voertuig","Tariff":"Tarief","Proposed · pale color":"Voorgesteld","Accepted · solid color":"Geaccepteerd","Measured · physical source":"Gemeten","Indicative · dashed outline":"Indicatief","Add asset":"Voertuig toevoegen","Add charger":"Laadpaal toevoegen","Charging mode":"Laadmodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blauw","orange":"Oranje","green":"Groen","purple":"Paars","gold":"Goud","teal":"Blauwgroen","pink":"Roze","indigo":"Indigo","olive":"Olijfgroen","brown":"Bruin","coral":"Koraal","slate":"Leigrijs","violet":"Violet","lime":"Limoen","salmon":"Zalm","cyan":"Cyaan","wine":"Wijnrood","forest":"Bosgroen","peach":"Perzik","lavender":"Lavendel","turquoise":"Turkoois","rust":"Roest","navy":"Marineblauw","moss":"Mosgroen","Guest expired":"Gast verlopen","Ready":"Gereed","No tariff":"Geen tarief","No solar":"Geen zon","No deadline":"Geen eindtijd","No charging goal":"Geen laaddoel","Limited power":"Beperkt vermogen","No source":"Geen bron","No capacity":"Geen capaciteit","Wiring unknown":"Aansluiting onbekend","Guest":"Gast","Charged":"Geladen","Charging":"Laden","Stopped":"Gestopt","Confirmed":"Bevestigd","No action":"Geen actie","Reason":"Reden","Energy":"Energie","Repeat":"Herhalen","Measured session energy":"Sessie-energie","Last confirmed session":"Laatste sessie","Measured energy":"Gemeten energie","Verified cost":"Kosten","Current range":"Stroomsterkte","Measured confirmation":"Gemeten om","Control type":"Sturing","On/off":"Aan/uit","Variable current":"Variabele stroom","Unverified":"Onbekend","No charger assigned":"Geen laadpaal","Target battery %":"Doelbatterij %","Asset name":"Voertuignaam","Asset type":"Soort","Temporary guest":"Tijdelijke gast","Guest until":"Gast tot","Expected connection":"Verwachte aansluiting","Save charging site":"Laadlocatie opslaan","Save sources":"Bronnen opslaan","Maximum group kW":"Max. vermogen kW","Group power ceiling kW":"Max. vermogen kW","Site name":"Locatienaam","Parallel chargers":"Gelijktijdige laders","Save electrical limits":"Limieten opslaan","Electrical limits":"Limieten","Battery data":"Batterijbron","Rated power":"Nominaal vermogen","Phases":"Fasen","Active session":"Actieve sessie","Add a chargeable asset":"Voertuig toevoegen","Create asset":"Toevoegen","Cancel adding":"Annuleren","Remove":"Verwijderen","Effective charging power":"Effectief laadvermogen","Car":"Auto","Bicycle":"Fiets","Motorcycle":"Motorfiets","Scooter":"Scooter","Other":"Overig","No active plan":"Geen actieve planning","Confirm connected vehicle":"Bevestig aangesloten voertuig","Connected vehicle":"Aangesloten voertuig","Not confirmed":"Niet bevestigd"},"fr":{"Overview":"Vue d’ensemble","Charging Plan":"Plan de charge","Chargeable Assets":"Véhicules","Chargers":"Bornes","Settings":"Réglages","Charging plan":"Plan de charge","Charging overview":"Vue des charges","Refresh":"Actualiser","Today":"Aujourd’hui","Tomorrow":"Demain","All chargers":"Toutes les bornes","Show labels":"Afficher","Color by":"Couleur par","Indicative forecasting":"Prévision","Vehicle":"Véhicule","Charger":"Borne","Vehicle + Charger":"Véhicule + borne","Show (not reserved)":"Afficher","Hide":"Masquer","Proposed":"Proposé","Accepted":"Confirmé","Measured":"Mesuré","Indicative":"Indicatif","No vehicle selected":"Aucun véhicule","Connected":"Connecté","Disconnected":"Déconnecté","Connection unknown":"Connexion inconnue","Vehicle unknown":"Véhicule inconnu","Unavailable":"Indisponible","Unknown":"Inconnu","Not set":"Non défini","Not assigned":"Non attribué","Plan color":"Couleur du plan","Plan labels":"Libellés du plan","Active chargers":"Bornes actives","Actual power":"Puissance réelle","Current price":"Tarif actuel","Charging strategy":"Mode de charge","Charging site":"Site de recharge","Sources & bindings":"Sources","Safety & limits":"Sécurité et limites","Integrations":"Intégrations","Advanced & YAML":"Avancé","Readiness":"Disponibilité","Battery":"Batterie","Target":"Cible","Ready By":"Prêt pour","Priority":"Priorité","Duration":"Durée","Requested energy":"Énergie demandée","Charging intention":"Besoin de charge","Charging priority":"Priorité","Connection":"Connexion","Selected vehicle":"Véhicule choisi","Assigned asset":"Véhicule choisi","Actual current":"Courant réel","Power":"Puissance","Source state":"État de la source","Status":"État","Start charging":"Démarrer","Stop charging":"Arrêter","Details":"Détails","Hide details":"Fermer","Edit":"Modifier","Saved":"Enregistré","Pending":"En attente","Rejected":"Refusé","Next planned session":"Prochaine charge","Next action":"Prochaine étape","No active qualified vehicle plan":"Aucune charge prévue","No qualified slots for this day.":"Aucun créneau","No vehicles":"Aucun véhicule","No charging points":"Aucune borne","Loading":"Chargement","Error":"Erreur","No data":"Aucune donnée","No connection":"Déconnecté","Not ready":"Non prêt","Waiting":"En attente","Forecast":"Prévision","If connected now":"Si connecté maintenant","Expected":"Prévu","Not reserved":"Non réservé","Measured power unavailable":"Mesure indisponible","Vehicle plan":"Plan véhicule","Charger plan":"Plan borne","No forecast":"Aucune prévision","No vehicle":"Aucun véhicule","Tariff":"Tarif","Proposed · pale color":"Proposé","Accepted · solid color":"Accepté","Measured · physical source":"Mesuré","Indicative · dashed outline":"Indicatif","Add asset":"Ajouter un véhicule","Add charger":"Ajouter borne","Charging mode":"Mode de charge","Mode":"Mode","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Bleu","orange":"Orange","green":"Vert","purple":"Violet","gold":"Or","teal":"Sarcelle","pink":"Rose","indigo":"Indigo","olive":"Olive","brown":"Marron","coral":"Corail","slate":"Ardoise","violet":"Mauve","lime":"Citron vert","salmon":"Saumon","cyan":"Cyan","wine":"Bordeaux","forest":"Vert forêt","peach":"Pêche","lavender":"Lavande","turquoise":"Turquoise","rust":"Rouille","navy":"Bleu marine","moss":"Vert mousse","Guest expired":"Invité expiré","Ready":"Prêt","No tariff":"Aucun tarif","No solar":"Pas de solaire","No deadline":"Pas d’échéance","No charging goal":"Aucune cible","Limited power":"Puissance limitée","No source":"Aucune source","No capacity":"Pas de capacité","Wiring unknown":"Câblage inconnu","Guest":"Invité","Charged":"Chargé","Charging":"Recharge","Stopped":"Arrêté","Confirmed":"Confirmé","No action":"Aucune action","Reason":"Motif","Energy":"Énergie","Repeat":"Répéter","Measured session energy":"Énergie de session","Last confirmed session":"Dernière session","Measured energy":"Énergie mesurée","Verified cost":"Coût","Current range":"Plage de courant","Measured confirmation":"Mesuré à","Control type":"Commande","On/off":"Marche/arrêt","Variable current":"Courant variable","Unverified":"Inconnu","No charger assigned":"Aucune borne","Target battery %":"Batterie cible %","Asset name":"Nom du véhicule","Asset type":"Type","Temporary guest":"Invité temporaire","Guest until":"Invité jusqu’à","Expected connection":"Connexion prévue","Save charging site":"Enregistrer le site","Save sources":"Enregistrer les sources","Maximum group kW":"Puissance max. kW","Group power ceiling kW":"Puissance max. kW","Site name":"Nom du site","Parallel chargers":"Bornes simultanées","Save electrical limits":"Enregistrer les limites","Electrical limits":"Limites","Battery data":"Source batterie","Rated power":"Puissance nominale","Phases":"Phases","Active session":"Session active","Add a chargeable asset":"Ajouter un véhicule","Create asset":"Ajouter","Cancel adding":"Annuler","Remove":"Supprimer","Effective charging power":"Puissance de charge effective","Car":"Voiture","Bicycle":"Vélo","Motorcycle":"Moto","Scooter":"Trottinette","Other":"Autre","No active plan":"Aucune charge planifiée","Confirm connected vehicle":"Confirmer le véhicule branché","Connected vehicle":"Véhicule branché","Not confirmed":"Non confirmé"},"da":{"Overview":"Overblik","Charging Plan":"Ladeplan","Chargeable Assets":"Køretøjer","Chargers":"Ladere","Settings":"Indstillinger","Charging plan":"Ladeplan","Charging overview":"Ladeoversigt","Refresh":"Opdater","Today":"I dag","Tomorrow":"I morgen","All chargers":"Alle ladere","Show labels":"Vis etiketter","Color by":"Farve efter","Indicative forecasting":"Prognose","Vehicle":"Køretøj","Charger":"Lader","Vehicle + Charger":"Køretøj + lader","Show (not reserved)":"Vis","Hide":"Skjul","Proposed":"Foreslået","Accepted":"Accepteret","Measured":"Målt","Indicative":"Vejledende","No vehicle selected":"Intet køretøj valgt","Connected":"Tilsluttet","Disconnected":"Ikke tilsluttet","Connection unknown":"Tilslutning ukendt","Vehicle unknown":"Køretøj ukendt","Unavailable":"Ikke tilgængelig","Unknown":"Ukendt","Not set":"Ikke angivet","Not assigned":"Ikke tildelt","Plan color":"Planfarve","Plan labels":"Planetiketter","Active chargers":"Aktive ladere","Actual power":"Aktuel effekt","Current price":"Aktuel pris","Charging strategy":"Ladetilstand","Charging site":"Ladested","Sources & bindings":"Kilder","Safety & limits":"Sikkerhed og grænser","Integrations":"Integrationer","Advanced & YAML":"Avanceret","Readiness":"Klar","Battery":"Batteri","Target":"Mål","Ready By":"Klar kl.","Priority":"Prioritet","Duration":"Varighed","Requested energy":"Ønsket energi","Charging intention":"Ladebehov","Charging priority":"Ladeprioritet","Connection":"Tilslutning","Selected vehicle":"Valgt køretøj","Assigned asset":"Tildelt køretøj","Actual current":"Aktuel strøm","Power":"Effekt","Source state":"Kildestatus","Status":"Status","Start charging":"Start opladning","Stop charging":"Stop opladning","Details":"Detaljer","Hide details":"Skjul detaljer","Edit":"Rediger","Saved":"Gemt","Pending":"Afventer","Rejected":"Afvist","Next planned session":"Næste planlagte opladning","Next action":"Næste handling","No active qualified vehicle plan":"Ingen aktiv ladeplan","No qualified slots for this day.":"Ingen ladetider","No vehicles":"Ingen køretøjer","No charging points":"Ingen ladere","Loading":"Indlæser","Error":"Fejl","No data":"Ingen data","No connection":"Ikke tilsluttet","Not ready":"Ikke klar","Waiting":"Venter","Forecast":"Prognose","If connected now":"Hvis tilsluttet nu","Expected":"Forventet","Not reserved":"Ikke reserveret","Measured power unavailable":"Ingen måledata","Vehicle plan":"Køretøjsplan","Charger plan":"Ladeplan","No forecast":"Ingen prognose","No vehicle":"Intet køretøj","Tariff":"Tarif","Proposed · pale color":"Foreslået","Accepted · solid color":"Accepteret","Measured · physical source":"Målt","Indicative · dashed outline":"Vejledende","Add asset":"Tilføj køretøj","Add charger":"Tilføj lader","Charging mode":"Ladetilstand","Mode":"Tilstand","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Orange","green":"Grøn","purple":"Lilla","gold":"Guld","teal":"Blågrøn","pink":"Pink","indigo":"Indigo","olive":"Oliven","brown":"Brun","coral":"Koral","slate":"Skifer","violet":"Violet","lime":"Lime","salmon":"Laks","cyan":"Cyan","wine":"Vinrød","forest":"Skovgrøn","peach":"Fersken","lavender":"Lavendel","turquoise":"Turkis","rust":"Rust","navy":"Marineblå","moss":"Mosgrøn","Guest expired":"Gæst udløbet","Ready":"Klar","No tariff":"Ingen tarif","No solar":"Ingen sol","No deadline":"Ingen frist","No charging goal":"Intet lademål","Limited power":"Begrænset effekt","No source":"Ingen kilde","No capacity":"Ingen kapacitet","Wiring unknown":"Ukendt ledningsføring","Guest":"Gæst","Charged":"Opladet","Charging":"Oplader","Stopped":"Stoppet","Confirmed":"Bekræftet","No action":"Ingen handling","Reason":"Årsag","Energy":"Energi","Repeat":"Gentag","Measured session energy":"Målt sessionsenergi","Last confirmed session":"Sidste session","Measured energy":"Målt energi","Verified cost":"Bekræftet pris","Current range":"Strømområde","Measured confirmation":"Målt kl.","Control type":"Styringstype","On/off":"Til/fra","Variable current":"Variabel strøm","Unverified":"Ikke verificeret","No charger assigned":"Ingen lader valgt","Target battery %":"Målbatteri %","Asset name":"Køretøjsnavn","Asset type":"Køretøjstype","Temporary guest":"Midlertidig gæst","Guest until":"Gæst indtil","Expected connection":"Forventet tilslutning","Save charging site":"Gem ladested","Save sources":"Gem kilder","Maximum group kW":"Maks. effekt kW","Group power ceiling kW":"Effektgrænse kW","Site name":"Stedsnavn","Parallel chargers":"Samtidige ladere","Save electrical limits":"Gem elektriske grænser","Electrical limits":"Elektriske grænser","Battery data":"Batterikilde","Rated power":"Nominel effekt","Phases":"Faser","Active session":"Aktiv session","Add a chargeable asset":"Tilføj køretøj","Create asset":"Opret køretøj","Cancel adding":"Annuller","Remove":"Fjern","Effective charging power":"Effektiv ladeeffekt","Car":"Bil","Bicycle":"Cykel","Motorcycle":"Motorcykel","Scooter":"Scooter","Other":"Andet","No active plan":"Ingen aktiv ladeplan","Confirm connected vehicle":"Bekræft tilsluttet køretøj","Connected vehicle":"Tilsluttet køretøj","Not confirmed":"Ikke bekræftet"},"nb":{"Overview":"Oversikt","Charging Plan":"Ladeplan","Chargeable Assets":"Kjøretøy","Chargers":"Ladere","Settings":"Innstillinger","Charging plan":"Ladeplan","Charging overview":"Ladeoversikt","Refresh":"Oppdater","Today":"I dag","Tomorrow":"I morgen","All chargers":"Alle ladere","Show labels":"Vis etiketter","Color by":"Farge etter","Indicative forecasting":"Prognose","Vehicle":"Kjøretøy","Charger":"Lader","Vehicle + Charger":"Kjøretøy + lader","Show (not reserved)":"Vis","Hide":"Skjul","Proposed":"Foreslått","Accepted":"Godkjent","Measured":"Målt","Indicative":"Veiledende","No vehicle selected":"Ingen kjøretøy valgt","Connected":"Tilkoblet","Disconnected":"Ikke tilkoblet","Connection unknown":"Tilkobling ukjent","Vehicle unknown":"Kjøretøy ukjent","Unavailable":"Ikke tilgjengelig","Unknown":"Ukjent","Not set":"Ikke angitt","Not assigned":"Ikke tilordnet","Plan color":"Planfarge","Plan labels":"Planetiketter","Active chargers":"Aktive ladere","Actual power":"Faktisk effekt","Current price":"Gjeldende pris","Charging strategy":"Lademodus","Charging site":"Ladested","Sources & bindings":"Kilder","Safety & limits":"Sikkerhet og grenser","Integrations":"Integrasjoner","Advanced & YAML":"Avansert","Readiness":"Klar","Battery":"Batteri","Target":"Mål","Ready By":"Klar innen","Priority":"Prioritet","Duration":"Varighet","Requested energy":"Ønsket energi","Charging intention":"Ladebehov","Charging priority":"Ladeprioritet","Connection":"Tilkobling","Selected vehicle":"Valgt kjøretøy","Assigned asset":"Tilordnet kjøretøy","Actual current":"Faktisk strøm","Power":"Effekt","Source state":"Kildestatus","Status":"Status","Start charging":"Start lading","Stop charging":"Stopp lading","Details":"Detaljer","Hide details":"Skjul detaljer","Edit":"Rediger","Saved":"Lagret","Pending":"Venter","Rejected":"Avvist","Next planned session":"Neste planlagte lading","Next action":"Neste handling","No active qualified vehicle plan":"Ingen aktiv ladeplan","No qualified slots for this day.":"Ingen ladetider","No vehicles":"Ingen kjøretøy","No charging points":"Ingen ladere","Loading":"Laster","Error":"Feil","No data":"Ingen data","No connection":"Ikke tilkoblet","Not ready":"Ikke klar","Waiting":"Venter","Forecast":"Prognose","If connected now":"Hvis tilkoblet nå","Expected":"Forventet","Not reserved":"Ikke reservert","Measured power unavailable":"Ingen måledata","Vehicle plan":"Kjøretøyplan","Charger plan":"Ladeplan","No forecast":"Ingen prognose","No vehicle":"Ingen kjøretøy","Tariff":"Pris","Proposed · pale color":"Foreslått","Accepted · solid color":"Godkjent","Measured · physical source":"Målt","Indicative · dashed outline":"Veiledende","Add asset":"Legg til kjøretøy","Add charger":"Legg til lader","Charging mode":"Lademodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Oransje","green":"Grønn","purple":"Lilla","gold":"Gull","teal":"Blågrønn","pink":"Rosa","indigo":"Indigo","olive":"Oliven","brown":"Brun","coral":"Korall","slate":"Skifer","violet":"Fiolett","lime":"Lime","salmon":"Laks","cyan":"Cyan","wine":"Vinrød","forest":"Skoggrønn","peach":"Fersken","lavender":"Lavendel","turquoise":"Turkis","rust":"Rust","navy":"Marineblå","moss":"Mosegrønn","Guest expired":"Gjest utløpt","Ready":"Klar","No tariff":"Ingen pris","No solar":"Ingen sol","No deadline":"Ingen frist","No charging goal":"Ingen lademål","Limited power":"Begrenset effekt","No source":"Ingen kilde","No capacity":"Ingen kapasitet","Wiring unknown":"Ukjent kabling","Guest":"Gjest","Charged":"Ladet","Charging":"Lader","Stopped":"Stoppet","Confirmed":"Bekreftet","No action":"Ingen handling","Reason":"Årsak","Energy":"Energi","Repeat":"Gjenta","Measured session energy":"Målt øktenergi","Last confirmed session":"Siste økt","Measured energy":"Målt energi","Verified cost":"Bekreftet kostnad","Current range":"Strømområde","Measured confirmation":"Målt kl.","Control type":"Styringstype","On/off":"Av/på","Variable current":"Variabel strøm","Unverified":"Ikke verifisert","No charger assigned":"Ingen lader valgt","Target battery %":"Batterimål %","Asset name":"Kjøretøynavn","Asset type":"Kjøretøytype","Temporary guest":"Midlertidig gjest","Guest until":"Gjest til","Expected connection":"Forventet tilkobling","Save charging site":"Lagre ladested","Save sources":"Lagre kilder","Maximum group kW":"Maks. effekt kW","Group power ceiling kW":"Effektgrense kW","Site name":"Stedsnavn","Parallel chargers":"Samtidige ladere","Save electrical limits":"Lagre grenser","Electrical limits":"Elektriske grenser","Battery data":"Batterikilde","Rated power":"Nominell effekt","Phases":"Faser","Active session":"Aktiv økt","Add a chargeable asset":"Legg til kjøretøy","Create asset":"Opprett kjøretøy","Cancel adding":"Avbryt","Remove":"Fjern","Effective charging power":"Effektiv ladeeffekt","Car":"Bil","Bicycle":"Sykkel","Motorcycle":"Motorsykkel","Scooter":"Sparkesykkel","Other":"Annet","No active plan":"Ingen aktiv ladeplan","Confirm connected vehicle":"Bekreft tilkoblet kjøretøy","Connected vehicle":"Tilkoblet kjøretøy","Not confirmed":"Ikke bekreftet"},"sv":{"Overview":"Översikt","Charging Plan":"Laddplan","Chargeable Assets":"Fordon","Chargers":"Laddare","Settings":"Inställningar","Charging plan":"Laddplan","Charging overview":"Laddöversikt","Refresh":"Uppdatera","Today":"I dag","Tomorrow":"I morgon","All chargers":"Alla laddare","Show labels":"Visa etiketter","Color by":"Färg efter","Indicative forecasting":"Prognos","Vehicle":"Fordon","Charger":"Laddare","Vehicle + Charger":"Fordon + laddare","Show (not reserved)":"Visa","Hide":"Dölj","Proposed":"Föreslaget","Accepted":"Godkänt","Measured":"Mätt","Indicative":"Preliminärt","No vehicle selected":"Inget fordon valt","Connected":"Ansluten","Disconnected":"Inte ansluten","Connection unknown":"Anslutning okänd","Vehicle unknown":"Fordon okänt","Unavailable":"Inte tillgänglig","Unknown":"Okänd","Not set":"Inte angiven","Not assigned":"Inte tilldelad","Plan color":"Planfärg","Plan labels":"Planetiketter","Active chargers":"Aktiva laddare","Actual power":"Faktisk effekt","Current price":"Aktuellt pris","Charging strategy":"Laddläge","Charging site":"Laddplats","Sources & bindings":"Källor","Safety & limits":"Säkerhet och gränser","Integrations":"Integrationer","Advanced & YAML":"Avancerat","Readiness":"Redo","Battery":"Batteri","Target":"Mål","Ready By":"Klar senast","Priority":"Prioritet","Duration":"Varaktighet","Requested energy":"Önskad energi","Charging intention":"Laddbehov","Charging priority":"Laddprioritet","Connection":"Anslutning","Selected vehicle":"Valt fordon","Assigned asset":"Tilldelat fordon","Actual current":"Faktisk ström","Power":"Effekt","Source state":"Källstatus","Status":"Status","Start charging":"Starta laddning","Stop charging":"Stoppa laddning","Details":"Detaljer","Hide details":"Dölj detaljer","Edit":"Ändra","Saved":"Sparat","Pending":"Väntar","Rejected":"Avvisat","Next planned session":"Nästa planerade laddning","Next action":"Nästa åtgärd","No active qualified vehicle plan":"Ingen aktiv laddplan","No qualified slots for this day.":"Inga laddtider","No vehicles":"Inga fordon","No charging points":"Inga laddare","Loading":"Läser in","Error":"Fel","No data":"Inga data","No connection":"Inte ansluten","Not ready":"Inte redo","Waiting":"Väntar","Forecast":"Prognos","If connected now":"Om ansluten nu","Expected":"Förväntad","Not reserved":"Inte reserverad","Measured power unavailable":"Inga mätdata","Vehicle plan":"Fordonsplan","Charger plan":"Laddplan","No forecast":"Ingen prognos","No vehicle":"Inget fordon","Tariff":"Pris","Proposed · pale color":"Föreslaget","Accepted · solid color":"Godkänt","Measured · physical source":"Mätt","Indicative · dashed outline":"Preliminärt","Add asset":"Lägg till fordon","Add charger":"Lägg till laddare","Charging mode":"Laddläge","Mode":"Läge","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Orange","green":"Grön","purple":"Lila","gold":"Guld","teal":"Blågrön","pink":"Rosa","indigo":"Indigo","olive":"Oliv","brown":"Brun","coral":"Korall","slate":"Skiffer","violet":"Violett","lime":"Lime","salmon":"Lax","cyan":"Cyan","wine":"Vinröd","forest":"Skogsgrön","peach":"Persika","lavender":"Lavendel","turquoise":"Turkos","rust":"Rost","navy":"Marinblå","moss":"Mossgrön","Guest expired":"Gäst utgången","Ready":"Redo","No tariff":"Inget pris","No solar":"Ingen sol","No deadline":"Ingen tidsgräns","No charging goal":"Inget laddmål","Limited power":"Begränsad effekt","No source":"Ingen källa","No capacity":"Ingen kapacitet","Wiring unknown":"Okänd ledning","Guest":"Gäst","Charged":"Laddad","Charging":"Laddar","Stopped":"Stoppad","Confirmed":"Bekräftad","No action":"Ingen åtgärd","Reason":"Orsak","Energy":"Energi","Repeat":"Upprepa","Measured session energy":"Uppmätt sessionsenergi","Last confirmed session":"Senaste session","Measured energy":"Uppmätt energi","Verified cost":"Bekräftad kostnad","Current range":"Strömområde","Measured confirmation":"Mätt kl.","Control type":"Styrningstyp","On/off":"På/av","Variable current":"Variabel ström","Unverified":"Inte verifierad","No charger assigned":"Ingen laddare vald","Target battery %":"Batterimål %","Asset name":"Fordonsnamn","Asset type":"Fordonstyp","Temporary guest":"Tillfällig gäst","Guest until":"Gäst till","Expected connection":"Förväntad anslutning","Save charging site":"Spara laddplats","Save sources":"Spara källor","Maximum group kW":"Max. effekt kW","Group power ceiling kW":"Effektgräns kW","Site name":"Platsnamn","Parallel chargers":"Samtidiga laddare","Save electrical limits":"Spara gränser","Electrical limits":"Elektriska gränser","Battery data":"Batterikälla","Rated power":"Nominell effekt","Phases":"Faser","Active session":"Aktiv session","Add a chargeable asset":"Lägg till fordon","Create asset":"Skapa fordon","Cancel adding":"Avbryt","Remove":"Ta bort","Effective charging power":"Effektiv laddeffekt","Car":"Bil","Bicycle":"Cykel","Motorcycle":"Motorcykel","Scooter":"Elsparkcykel","Other":"Annat","No active plan":"Ingen aktiv laddplan","Confirm connected vehicle":"Bekräfta anslutet fordon","Connected vehicle":"Anslutet fordon","Not confirmed":"Inte bekräftat"},"de":{"Overview":"Übersicht","Charging Plan":"Ladeplan","Chargeable Assets":"Lade-Assets","Chargers":"Ladepunkte","Settings":"Einstellungen","Charging plan":"Ladeplan","Charging overview":"Ladeübersicht","Refresh":"Aktualisieren","Today":"Heute","Tomorrow":"Morgen","All chargers":"Alle Ladepunkte","Show labels":"Beschriftung","Color by":"Farbe nach","Indicative forecasting":"Prognose","Vehicle":"Asset","Charger":"Ladepunkt","Vehicle + Charger":"Asset + Ladepunkt","Show (not reserved)":"Anzeigen","Hide":"Ausblenden","Proposed":"Vorgeschlagen","Accepted":"Angenommen","Measured":"Gemessen","Indicative":"Unverbindlich","No vehicle selected":"Kein Asset gewählt","Connected":"Verbunden","Disconnected":"Nicht verbunden","Connection unknown":"Verbindung unbekannt","Vehicle unknown":"Asset unbekannt","Unavailable":"Nicht verfügbar","Unknown":"Unbekannt","Not set":"Nicht festgelegt","Not assigned":"Nicht zugewiesen","Plan color":"Planfarbe","Plan labels":"Planbeschriftung","Active chargers":"Aktive Ladepunkte","Actual power":"Ist-Leistung","Current price":"Aktueller Preis","Charging strategy":"Lademodus","Charging site":"Ladestandort","Sources & bindings":"Quellen und Zuordnung","Safety & limits":"Sicherheit und Grenzen","Integrations":"Integrationen","Advanced & YAML":"Erweitert","Readiness":"Bereitschaft","Battery":"Batterie","Target":"Ziel","Ready By":"Bereit bis","Priority":"Priorität","Duration":"Dauer","Requested energy":"Energiebedarf","Charging intention":"Ladebedarf","Charging priority":"Ladepriorität","Connection":"Verbindung","Selected vehicle":"Ausgewähltes Asset","Assigned asset":"Zugeordnetes Asset","Actual current":"Ist-Strom","Power":"Leistung","Source state":"Quellenstatus","Status":"Status","Start charging":"Laden starten","Stop charging":"Laden stoppen","Details":"Details","Hide details":"Details schließen","Edit":"Bearbeiten","Saved":"Gespeichert","Pending":"Ausstehend","Rejected":"Abgelehnt","Next planned session":"Nächste Ladesitzung","Next action":"Nächste Aktion","No active qualified vehicle plan":"Kein aktiver Ladeplan","No qualified slots for this day.":"Keine Ladezeiten","No vehicles":"Keine Assets","No charging points":"Keine Ladepunkte","Loading":"Lädt","Error":"Fehler","No data":"Keine Daten","No connection":"Nicht verbunden","Not ready":"Nicht bereit","Waiting":"Warten","Forecast":"Prognose","If connected now":"Falls jetzt verbunden","Expected":"Erwartet","Not reserved":"Nicht reserviert","Measured power unavailable":"Keine Messdaten","Vehicle plan":"Assetplan","Charger plan":"Ladepunktplan","No forecast":"Keine Prognose","No vehicle":"Kein Asset","Tariff":"Tarif","Proposed · pale color":"Vorgeschlagen","Accepted · solid color":"Angenommen","Measured · physical source":"Gemessen","Indicative · dashed outline":"Unverbindlich","Add asset":"Asset hinzufügen","Add charger":"Ladepunkt hinzufügen","Charging mode":"Lademodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","Guest expired":"Gast abgelaufen","Ready":"Bereit","No tariff":"Kein Tarif","No solar":"Kein Solar","No deadline":"Keine Frist","No charging goal":"Kein Ladeziel","Limited power":"Begrenzte Leistung","No source":"Keine Quelle","No capacity":"Keine Kapazität","Wiring unknown":"Verdrahtung unbekannt","Guest":"Gast","Charged":"Geladen","Charging":"Lädt","Stopped":"Gestoppt","Confirmed":"Bestätigt","No action":"Keine Aktion","Reason":"Grund","Energy":"Energie","Repeat":"Wiederholen","Measured session energy":"Gemessene Sitzungsenergie","Last confirmed session":"Letzte bestätigte Sitzung","Measured energy":"Gemessene Energie","Verified cost":"Verifizierte Kosten","Current range":"Strombereich","Measured confirmation":"Messzeit","Control type":"Steuerungstyp","On/off":"Ein/Aus","Variable current":"Variabler Strom","Unverified":"Nicht verifiziert","No charger assigned":"Kein Ladepunkt zugewiesen","Target battery %":"Batterieziel %","Asset name":"Assetname","Asset type":"Assettyp","Temporary guest":"Temporärer Gast","Guest until":"Gast bis","Expected connection":"Erwartete Verbindung","Save charging site":"Ladestandort speichern","Save sources":"Quellen speichern","Maximum group kW":"Maximale Gruppenleistung kW","Group power ceiling kW":"Gruppenleistungsgrenze kW","Site name":"Standortname","Parallel chargers":"Gleichzeitige Ladepunkte","Save electrical limits":"Elektrische Grenzen speichern","Electrical limits":"Elektrische Grenzen","Battery data":"Batteriedaten","Rated power":"Nennleistung","Phases":"Phasen","Active session":"Aktive Sitzung","Add a chargeable asset":"Lade-Asset hinzufügen","Create asset":"Asset erstellen","Cancel adding":"Abbrechen","Remove":"Entfernen","blue":"Blau","orange":"Orange","green":"Grün","purple":"Lila","gold":"Gold","teal":"Blaugrün","pink":"Rosa","indigo":"Indigo","olive":"Oliv","brown":"Braun","coral":"Koralle","slate":"Schiefer","violet":"Violett","lime":"Limette","salmon":"Lachs","cyan":"Cyan","wine":"Weinrot","forest":"Waldgrün","peach":"Pfirsich","lavender":"Lavendel","turquoise":"Türkis","rust":"Rost","navy":"Marineblau","moss":"Moosgrün","Effective charging power":"Effektive Ladeleistung","Car":"Auto","Bicycle":"Fahrrad","Motorcycle":"Motorrad","Scooter":"Roller","Other":"Sonstiges","No active plan":"Kein aktiver Ladeplan","Confirm connected vehicle":"Angeschlossenes Fahrzeug bestätigen","Connected vehicle":"Angeschlossenes Fahrzeug","Not confirmed":"Nicht bestätigt"},"es":{"Overview":"Resumen","Charging Plan":"Plan de carga","Chargeable Assets":"Activos de carga","Chargers":"Puntos de carga","Settings":"Ajustes","Charging plan":"Plan de carga","Charging overview":"Resumen de carga","Refresh":"Actualizar","Today":"Hoy","Tomorrow":"Mañana","All chargers":"Todos los puntos","Show labels":"Mostrar etiquetas","Color by":"Color por","Indicative forecasting":"Previsión","Vehicle":"Activo","Charger":"Punto de carga","Vehicle + Charger":"Activo + punto","Show (not reserved)":"Mostrar","Hide":"Ocultar","Proposed":"Propuesto","Accepted":"Aceptado","Measured":"Medido","Indicative":"Indicativo","No vehicle selected":"Ningún activo seleccionado","Connected":"Conectado","Disconnected":"Desconectado","Connection unknown":"Conexión desconocida","Vehicle unknown":"Activo desconocido","Unavailable":"No disponible","Unknown":"Desconocido","Not set":"Sin definir","Not assigned":"Sin asignar","Plan color":"Color del plan","Plan labels":"Etiquetas del plan","Active chargers":"Puntos activos","Actual power":"Potencia real","Current price":"Precio actual","Charging strategy":"Modo de carga","Charging site":"Instalación de carga","Sources & bindings":"Fuentes y asignación","Safety & limits":"Seguridad y límites","Integrations":"Integraciones","Advanced & YAML":"Avanzado","Readiness":"Preparación","Battery":"Batería","Target":"Objetivo","Ready By":"Listo para","Priority":"Prioridad","Duration":"Duración","Requested energy":"Energía solicitada","Charging intention":"Necesidad de carga","Charging priority":"Prioridad de carga","Connection":"Conexión","Selected vehicle":"Activo seleccionado","Assigned asset":"Activo asignado","Actual current":"Corriente real","Power":"Potencia","Source state":"Estado de fuente","Status":"Estado","Start charging":"Iniciar carga","Stop charging":"Detener carga","Details":"Detalles","Hide details":"Cerrar detalles","Edit":"Editar","Saved":"Guardado","Pending":"Pendiente","Rejected":"Rechazado","Next planned session":"Próxima carga","Next action":"Siguiente acción","No active qualified vehicle plan":"Sin plan activo","No qualified slots for this day.":"Sin franjas de carga","No vehicles":"Sin activos","No charging points":"Sin puntos de carga","Loading":"Cargando","Error":"Error","No data":"Sin datos","No connection":"Sin conexión","Not ready":"No preparado","Waiting":"Esperando","Forecast":"Previsión","If connected now":"Si se conecta ahora","Expected":"Previsto","Not reserved":"No reservado","Measured power unavailable":"Sin datos medidos","Vehicle plan":"Plan por activo","Charger plan":"Plan por punto","No forecast":"Sin previsión","No vehicle":"Sin activo","Tariff":"Tarifa","Proposed · pale color":"Propuesto","Accepted · solid color":"Aceptado","Measured · physical source":"Medido","Indicative · dashed outline":"Indicativo","Add asset":"Añadir activo","Add charger":"Añadir punto","Charging mode":"Modo de carga","Mode":"Modo","Plan":"Plan","Home Assistant":"Home Assistant","Guest expired":"Invitado caducado","Ready":"Listo","No tariff":"Sin tarifa","No solar":"Sin energía solar","No deadline":"Sin plazo","No charging goal":"Sin objetivo","Limited power":"Potencia limitada","No source":"Sin fuente","No capacity":"Sin capacidad","Wiring unknown":"Cableado desconocido","Guest":"Invitado","Charged":"Cargado","Charging":"Cargando","Stopped":"Detenido","Confirmed":"Confirmado","No action":"Sin acción","Reason":"Motivo","Energy":"Energía","Repeat":"Repetir","Measured session energy":"Energía medida de sesión","Last confirmed session":"Última sesión confirmada","Measured energy":"Energía medida","Verified cost":"Coste verificado","Current range":"Rango de corriente","Measured confirmation":"Confirmación medida","Control type":"Tipo de control","On/off":"Encendido/apagado","Variable current":"Corriente variable","Unverified":"No verificado","No charger assigned":"Sin punto asignado","Target battery %":"Batería objetivo %","Asset name":"Nombre del activo","Asset type":"Tipo de activo","Temporary guest":"Invitado temporal","Guest until":"Invitado hasta","Expected connection":"Conexión prevista","Save charging site":"Guardar instalación","Save sources":"Guardar fuentes","Maximum group kW":"Potencia máxima del grupo kW","Group power ceiling kW":"Límite del grupo kW","Site name":"Nombre del lugar","Parallel chargers":"Puntos simultáneos","Save electrical limits":"Guardar límites","Electrical limits":"Límites eléctricos","Battery data":"Datos de batería","Rated power":"Potencia nominal","Phases":"Fases","Active session":"Sesión activa","Add a chargeable asset":"Añadir activo de carga","Create asset":"Crear activo","Cancel adding":"Cancelar","Remove":"Eliminar","blue":"Azul","orange":"Naranja","green":"Verde","purple":"Morado","gold":"Dorado","teal":"Verde azulado","pink":"Rosa","indigo":"Índigo","olive":"Oliva","brown":"Marrón","coral":"Coral","slate":"Pizarra","violet":"Violeta","lime":"Lima","salmon":"Salmón","cyan":"Cian","wine":"Granate","forest":"Verde bosque","peach":"Melocotón","lavender":"Lavanda","turquoise":"Turquesa","rust":"Óxido","navy":"Azul marino","moss":"Verde musgo","Effective charging power":"Potencia efectiva de carga","Car":"Coche","Bicycle":"Bicicleta","Motorcycle":"Motocicleta","Scooter":"Patinete","Other":"Otro","No active plan":"Sin plan activo","Confirm connected vehicle":"Confirmar vehículo conectado","Connected vehicle":"Vehículo conectado","Not confirmed":"Sin confirmar"}};
function mcTr(value){
  const raw=String(value);
  return MC_TEXT[mcLanguage]?.[raw]||raw;
}
function mcOwnerColor(kind,id,configuration,palette){
  const rows=kind==="charger"?configuration.chargers:configuration.assets;
  const found=(rows||[]).find(x=>x.id===id);
  return found?.plan_color&&palette?.[found.plan_color]||
    "var(--secondary-text-color,#757d87)";
}

const MC_MODE_SELECT={
  Automatic:"automatic",Solar:"solar",Economy:"economy",
  "Ready By":"ready_by","Force Charge":"force_charge",Off:"off"
};
const MC_REASONS={
  DISCONNECTED:"Disconnected",CONNECTION_UNCONFIRMED:"Connection unknown",
  NO_CHARGEABLE_ASSET:"No vehicle",TEMPORARY_ASSET_EXPIRED:"Guest expired",
  OFF:"Off",PROPOSED:"Proposed",TARGET_MET:"Ready",PRICE_UNAVAILABLE:"No tariff",
  SOLAR_UNAVAILABLE:"No solar",DEADLINE_UNKNOWN:"No deadline",
  DEMAND_UNKNOWN:"No charging goal",INSUFFICIENT_CAPACITY_OR_TIME:"Limited power",
  SOURCE_NOT_SELECTED:"No source",BINDING_CAPACITY_UNAVAILABLE:"No capacity",
  PHASE_WIRING_UNVERIFIED:"Wiring unknown",NO_ASSIGNED_ASSET:"No vehicle"
};
function mcReason(value){return mcTr(MC_REASONS[value]||"Unavailable");}
const MC_TABS = ["Overview", "Charging Plan", "Chargeable Assets", "Chargers", "Settings"];
const MC_SETTINGS = ["Charging site", "Sources & bindings", "Charging strategy", "Safety & limits", "Integrations", "Advanced & YAML"];
const MC_MODES = ["Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"];
const MC_STYLE = [
  ":host{display:block;color:var(--primary-text-color,#20252b);font:inherit}",
  ".root{background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:16px;padding:16px;box-shadow:var(--ha-card-box-shadow,0 2px 8px #0002)}",
  ".heading{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}",
  "h2{font-size:20px;line-height:1.4;margin:0 0 8px}h3{font-size:16px;margin:0}p{margin:5px 0;line-height:1.5}",
  ".muted{color:var(--secondary-text-color,#65717e)}.small{font-size:12px}.value{font-weight:700;font-size:22px}",
  ".tabs,.controls,.chips{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}",
  "input,button,select,textarea,a.action{font:inherit;border:1px solid var(--divider-color,#cfd6de);background:var(--card-background-color,#fff);color:inherit;border-radius:10px;padding:9px 11px;cursor:pointer;text-decoration:none;min-height:42px}",
  "button[aria-selected=true],button.active{background:var(--primary-color,#1976d2);color:var(--text-primary-color,#fff);border-color:var(--primary-color,#1976d2)}",
  "button:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid var(--primary-color,#1976d2);outline-offset:2px}",
  ".grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}",
  ".card{border:1px solid var(--divider-color,#e1e4e8);border-radius:12px;padding:13px;min-width:0;margin:8px 0}",
  ".metric{background:var(--secondary-background-color,#f6f8fa);border-radius:12px;padding:12px;min-width:0}",
  ".row{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}",
  ".details{margin-top:10px;padding-top:9px;border-top:1px solid var(--divider-color,#ddd)}",
  ".pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:5px 0}",
  ".field{display:flex;flex-direction:column;gap:4px;margin:8px 0}.field label{font-size:13px;color:var(--secondary-text-color,#65717e)}",
  ".field input,.field select{width:100%;box-sizing:border-box;padding:10px;border:1px solid var(--divider-color,#cfd6de);background:var(--card-background-color,#fff);color:inherit;border-radius:8px}",
  ".message{font-size:13px;margin:9px 0}.pending{color:var(--warning-color,#b57418)}.confirmed{color:var(--success-color,#278355)}",
  ".notice{border-left:3px solid var(--warning-color,#e59e31);padding:9px 12px;background:var(--secondary-background-color,#f6f8fa);margin:12px 0;font-size:13px}",
  ".error{border-left-color:var(--error-color,#d43b38)}.chart{overflow-x:auto;width:100%}",
  ".legend{display:flex;flex-wrap:wrap;gap:15px;font-size:12px;color:var(--secondary-text-color,#65717e)}",
  ".dot{display:inline-block;width:11px;height:11px;margin-right:5px;border-radius:2px}",
  ".plan-lane{margin:10px 0;border:1px solid var(--divider-color,#d8dde3);border-radius:11px;padding:11px}",
  ".plan-lane svg{display:block;min-width:680px;width:100%;height:auto}",
  ".plan-lane .chart{margin-top:5px}",
  ".plan-key{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:6px 0;font-size:12px}",
  ".plan-swatch{width:12px;height:12px;border-radius:3px;display:inline-block;margin-right:4px}",
  ".plan-caution{font-size:12px;color:var(--secondary-text-color,#65717e);line-height:1.5}",
  "svg{width:100%;min-width:440px;height:220px}svg text{fill:var(--secondary-text-color,#65717e);font-size:11px}",
  "@media(max-width:600px){.root{padding:12px}.grid{grid-template-columns:1fr}.tabs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.tabs button{font-size:12px;padding:8px 5px}}"
].join("");

function mcEl(tag, css, text) {
  const node = document.createElement(tag);
  if (css) node.className = css;
  if (text !== undefined && text !== null) node.textContent = mcTr(text);
  return node;
}
function mcButton(text, action, css) {
  const node = mcEl("button", css || "", text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function mcValue(observation, suffix) {
  if (!observation || observation.quality !== "ok" || observation.value === null || observation.value === undefined) return mcTr("Unknown");
  if (typeof observation.value === "boolean") return mcTr(observation.value ? "Connected" : "Disconnected");
  return String(observation.value) + (suffix || "");
}
function mcTime(value, zone) {
  if (!value) return mcTr("Not set");
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? mcTr("Unknown") : date.toLocaleString(undefined, {timeZone: zone || "UTC", month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
}
function mcPair(target, left, right) {
  const pair=mcEl("div","pair");
  pair.append(mcEl("span","muted",left),mcEl("span","",right));
  target.append(pair);
}
function mcSVG(tag, attrs, text) {
  const node=document.createElementNS("http://www.w3.org/2000/svg",tag);
  for (const [name,value] of Object.entries(attrs||{})) node.setAttribute(name,String(value));
  if(text!==undefined)node.textContent=mcTr(text);
  return node;
}


function mcPlanName(slot,configuration,labels){
  const charger=(configuration.chargers||[]).find(c=>c.id===slot.charger_id);
  const asset=(configuration.assets||[]).find(a=>a.id===slot.asset_id);
  const car=asset?asset.name:(slot.asset_id||"Unidentified");
  const station=charger?charger.name:(slot.charger_id||"Unknown charger");
  return labels==="vehicle"?car:labels==="charger"?station:car+" · "+station;
}

class RobotixMultiChargeCard extends HTMLElement {
  constructor(){
    super();
    this.attachShadow({mode:"open"});
    this._tab="Overview";
    this._day="today";
    this._filter="";
    this._open="";
    this._settingsOpen="Charging site";
    this._data=null;
    this._error="";
    this._last=0;
    this._loading=false;
    this._commandBusy=false;
    this._commandFeedback={};
    this._settingsBusy=false;
    this._settingsFeedback=null;
    this._pendingSettings=null;
    this._assetEditor="";
  }
  setConfig(config){this._cardConfig=config||{};this.render();}
  getCardSize(){return 10;}
  set hass(value){
    this._hass=value;
    if(!this._loading&&(!this._last||Date.now()-this._last>60000)) this.load();
    else if(this._data) this.render();
  }
  async load(){
    if(!this._hass||this._loading)return;
    this._loading=true;this._error="";this.render();
    try {
      const cmd={type:"robotix_multicharge/get_plan",day:this._day};
      if(this._filter.startsWith("charger:"))cmd.charger_id=this._filter.slice(8);
      if(this._filter.startsWith("asset:"))cmd.asset_id=this._filter.slice(6);
      this._data=await this._hass.callWS(cmd);
      if(this._pendingSettings&&
         this._data.configuration_revision===this._pendingSettings.expected_revision){
        this._settingsFeedback={status:"confirmed",message:"Saved"};
        this._pendingSettings=null;
      }
      this._last=Date.now();
    }catch(error){
      this._error=error && (error.message||error.code) ? String(error.message||error.code) : "Read access unavailable";
      this._data=null;
      this._last=Date.now();
    }finally{this._loading=false;this.render();}
  }
  async command(charger,action){
    if(this._commandBusy||!this._hass)return;
    this._commandBusy=true;
    this._commandFeedback[charger]={status:"requested",reason:"Pending"};
    this.render();
    try {
      const request={type:"robotix_multicharge/command",
                     charger_id:charger,action};
      if(typeof crypto!=="undefined"&&typeof crypto.randomUUID==="function")
        request.request_id=crypto.randomUUID();
      const outcome=await this._hass.callWS(request);
      this._commandFeedback[charger]=outcome;
      if(outcome.status==="confirmed"){
        this._last=0;
        await this.load();
      }
    }catch(error){
      this._commandFeedback[charger]={
        status:"rejected",
        reason:"COMMAND_REQUEST_FAILED"
      };
    }finally{this._commandBusy=false;this.render();}
  }
  async saveSettings(scope,targetId,changes,action){
    if(this._settingsBusy||!this._hass||!this._data)return;
    if(!this._data.configuration_revision){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Pending"};
    this.render();
    try{
      const receipt=await this._hass.callWS({
        type:"robotix_multicharge/update_settings",
        scope,target_id:targetId,changes,action:action||"save",
        expected_revision:this._data.configuration_revision
      });
      if(receipt.status!=="accepted_unconfirmed"||!receipt.expected_revision)
        throw new Error("Settings change was not admitted");
      this._pendingSettings={expected_revision:receipt.expected_revision};
      this._settingsFeedback={status:"accepted_unconfirmed",message:"Pending"};
      this._last=0;
    }catch(error){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
    }finally{
      this._settingsBusy=false;
      if(this._pendingSettings)await this.load();
      this.render();
    }
  }
  ownerEntity(scope,uid,field){
    const prefs=this._data?.preference_entities||{};
    const group=scope==="controller"?prefs.controller:
      scope==="asset"?prefs.assets?.[uid]:prefs.chargers?.[uid];
    return group?.[field]||null;
  }
  async nativeSelect(scope,uid,field,option){
    const entity=this.ownerEntity(scope,uid,field);
    if(!entity||!this._hass?.callService){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Updating"};
    this.render();
    try{
      await this._hass.callService("select","select_option",{
        entity_id:entity,option:field==="mode"?MC_MODE_SELECT[option]||option:option
      });
      this._last=0;
      await this.load();
      this._settingsFeedback={status:"accepted_unconfirmed",message:"Updating"};
    }catch(error){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
    }finally{this._settingsBusy=false;this.render();}
  }
  async nativeButton(scope,uid,field){
    const entity=this.ownerEntity(scope,uid,field);
    if(!entity||!this._hass?.callService){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Pending"};
    this.render();
    try{
      await this._hass.callService("button","press",{entity_id:entity});
      this._last=0;
      await this.load();
      this._settingsFeedback={status:"confirmed",message:"Confirmed"};
    }catch(error){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
    }finally{this._settingsBusy=false;this.render();}
  }
  openNative(scope,uid,field){
    const entity=this.ownerEntity(scope,uid,field);
    if(!entity){this._settingsFeedback={status:"rejected",message:"Unavailable"};this.render();return;}
    this.dispatchEvent(new CustomEvent("hass-more-info",{
      bubbles:true,composed:true,detail:{entityId:entity}
    }));
  }
  ownerColorControl(container,scope,row){
    const palette=this._data?.plan_palette||{};
    const entity=this.ownerEntity(scope,row.id,"plan_color");
    const options=Object.keys(palette).map(key=>[key,mcTr(key)]);
    const pick=this.field(container,"Plan color",row.plan_color,null,options);
    pick.disabled=!entity||this._settingsBusy;
    pick.addEventListener("change",()=>this.nativeSelect(
      scope,row.id,"plan_color",pick.value
    ));
    return pick;
  }
  field(container,title,value,type,choices){
    const wrapper=mcEl("div","field"),label=mcEl("label","",title);
    const input=mcEl(choices?"select":"input");
    const id="multicharge-"+title.toLowerCase().replace(/[^a-z0-9]+/g,"-");
    input.setAttribute("id",id);label.setAttribute("for",id);
    if(choices){
      for(const [key,caption] of choices){
        const opt=mcEl("option","",caption);opt.value=key;
        if(key===String(value===null||value===undefined?"":value))opt.selected=true;
        input.append(opt);
      }
    }else{
      input.setAttribute("type",type||"text");
    }
    input.value=value===undefined||value===null?"":String(value);
    wrapper.append(label,input);container.append(wrapper);
    return input;
  }
  feedback(container){
    if(!this._settingsFeedback)return;
    const result=this._settingsFeedback;
    const node=mcEl("p","message "+(result.status==="confirmed"?"confirmed":result.status==="rejected"?"error":"pending"),
      result.status==="confirmed"?"Saved":result.status==="rejected"?"Unavailable":"Pending");
    node.setAttribute("role",result.status==="rejected"?"alert":"status");
    container.append(node);
  }
  title(container,label){
    container.append(mcEl("h2","",label));
  }
  notice(container,message,bad){
    container.append(mcEl("div","notice"+(bad?" error":""),message));
  }
  configure(container){
    const link=mcEl("a","action","Home Assistant");
    link.href="/config/integrations/integration/robotix_multicharge";
    link.setAttribute("aria-label",mcTr("Home Assistant"));
    container.append(link);
  }
  render(){
    mcLanguage=String(this._hass?.locale?.language||this._hass?.language||"en").slice(0,2).toLowerCase();
    if(!this.shadowRoot)return;
    const root=this.shadowRoot;root.replaceChildren();
    const style=mcEl("style");style.textContent=MC_STYLE;root.append(style);
    const shell=mcEl("section","root");
    const head=mcEl("div","heading");const heading=mcEl("div");
    heading.append(mcEl("h2","","MultiCharge"));
    head.append(heading,mcButton("Refresh",()=>{this._last=0;this.load();}));
    shell.append(head);
    const tabs=mcEl("nav","tabs");tabs.setAttribute("aria-label","MultiCharge views");
    for(const item of MC_TABS){
      const btn=mcButton(item,()=>{this._tab=item;this.render();});
      btn.setAttribute("aria-selected",String(this._tab===item));
      tabs.append(btn);
    }
    shell.append(tabs);
    if(this._loading&&!this._data)this.notice(shell,"Loading",false);
    if(this._error){
      this.notice(shell,"Unavailable",true);
      this.configure(shell);
    }else if(!this._data&&!this._loading){
      this.notice(shell,"Unavailable",true);
      this.configure(shell);
    }else if(this._data){
      if(this._tab==="Overview")this.overview(shell);
      if(this._tab==="Charging Plan")this.plan(shell);
      if(this._tab==="Chargeable Assets")this.assets(shell);
      if(this._tab==="Chargers")this.chargers(shell);
      if(this._tab==="Settings")this.settings(shell);

    }
    root.append(shell);
  }
  overview(container){
    const d=this._data,c=d.configuration||{},assets=c.assets||[],chargers=c.chargers||[];
    this.title(container,"Charging overview");
    const observations=(d.observations||{}).chargers||{};
    const priced=((d.observations||{}).sources||{}).current_price||{};
    const priceLabel=priced.quality==="ok"&&typeof priced.value==="number"&&priced.currency
      ?new Intl.NumberFormat(undefined,{style:"currency",currency:priced.currency,maximumFractionDigits:4}).format(priced.value)+"/kWh"
      :"Unavailable";
    const powers=chargers.map(x=>(observations[x.id]||{}).power_kw);
    const complete=powers.length>0&&powers.every(x=>x&&x.quality==="ok"&&typeof x.value==="number");
    const active=powers.filter(x=>x&&x.quality==="ok"&&x.value>0).length;
    const metrics=mcEl("div","grid");
    for(const [key,value] of [
      ["Active chargers",complete?String(active):"Unknown"],
      ["Actual power",complete?(powers.reduce((sum,x)=>sum+x.value,0).toFixed(2)+" kW"):"Unknown"],
      ["Current price",priceLabel]
    ]){const el=mcEl("div","metric");el.append(mcEl("p","muted small",key),mcEl("div","value",value));metrics.append(el);}
    container.append(metrics);
    const mode=(c.controller||{}).mode||"Off";
    const chips=mcEl("div","chips");chips.append(mcEl("p","muted",mcTr("Charging mode")+" · "+mode));
    for(const item of MC_MODES){
      const button=mcButton(item,()=>this.nativeSelect("controller",(c.controller||{}).id,"mode",item));
      button.disabled=this._settingsBusy||item===mode||!this.ownerEntity("controller",(c.controller||{}).id,"mode");
      button.title=mcTr("Charging mode");
      if(item===mode)button.className="active";
      chips.append(button);
    }
    container.append(chips);
    this.feedback(container);
    for(const a of assets){
      const card=mcEl("div","card");const observed=((d.observations||{}).assets||{})[a.id]||{};
      const charger=chargers.find(x=>x.asset===a.id);
      card.append(mcEl("h3","",a.name),mcEl("p","muted",mcTr("Battery")+" "+mcValue(observed.soc,"%")+" · "+mcTr("Target")+" "+(a.target_soc===undefined?mcTr("Not set"):a.target_soc+"%")));
      card.append(mcEl("p","small",mcTr("Ready By")+" "+mcTime(a.ready_by,d.timezone)+" · "+(charger?charger.name:mcTr("No charger assigned"))));
      if(a.temporary)card.append(mcEl("p","small",mcTr("Guest")+" · "+mcTime(a.expires_at,d.timezone)));
      container.append(card);
    }
    if(!assets.length)this.notice(container,"No data",false);
    const next=mcEl("div","card");next.append(mcEl("h3","","Next action"));
    next.append(mcEl("p","",d.status==="unavailable"?"Not ready":"Plan"));
    const reasons=Object.entries(d.reasons||{}).filter(([key,val])=>val!=="PROPOSED");
    if(reasons.length)next.append(mcEl("p","muted small",reasons.map(([key,val])=>key+": "+mcReason(val)).slice(0,4).join(" · ")));
    container.append(next);
  }
  settingsSelect(_container,name){this._tab="Settings";this._settingsOpen=name;this.render();}
  plan(container){
    const d=this._data,c=d.configuration||{},controller=c.controller||{};
    const cars=c.assets||[],chargers=c.chargers||[];
    const labelMode=controller.plan_label_mode||"both";
    const colorBy=controller.plan_color_by||"vehicle";
    const forecastVisible=controller.show_indicative_forecast!==false;
    this.title(container,"Charging plan");
    const day=mcEl("div","controls");
    for(const chosen of ["today","tomorrow"]){
      const b=mcButton(chosen==="today"?"Today":"Tomorrow",()=>{
        this._day=chosen;this._last=0;this.load();
      },this._day===chosen?"active":"");
      day.append(b);
    }
    const filter=mcEl("select");
    filter.setAttribute("aria-label","Filter by charger or vehicle");
    for(const [value,title] of [["","All chargers"],
      ...chargers.map(x=>["charger:"+x.id,x.name]),
      ...cars.map(x=>["asset:"+x.id,x.name+" (vehicle)"])]){
      const o=mcEl("option","",title);o.value=value;
      o.selected=this._filter===value;filter.append(o);
    }
    filter.value=this._filter;
    filter.addEventListener("change",()=>{this._filter=filter.value;this._last=0;this.load();});
    day.append(filter);container.append(day);
    const selectors=mcEl("div","controls");
    const option=(title,setting,value,variants)=>{
      const wrap=mcEl("div","field");const label=mcEl("label","",title);
      const select=mcEl("select");
      select.setAttribute("aria-label",title);
      for(const [id,caption] of variants){
        const entry=mcEl("option","",caption);entry.value=id;
        if(id===value)entry.selected=true;
        select.append(entry);
      }
      select.value=value;
      select.disabled=this._settingsBusy||!this.ownerEntity("controller",controller.id,setting);
      select.addEventListener("change",()=>{
        const selected=setting==="show_indicative_forecast"?
          select.value==="true":select.value;
        this.nativeSelect("controller",controller.id,setting,
          typeof selected==="boolean"?(selected?"on":"off"):selected);
      });
      wrap.append(label,select);selectors.append(wrap);
    };
    option("Show labels","plan_label_mode",labelMode,
      [["vehicle","Vehicle"],["charger","Charger"],["both","Vehicle + Charger"]]);
    option("Color by","plan_color_by",colorBy,
      [["vehicle","Vehicle"],["charger","Charger"]]);
    option("Indicative forecasting","show_indicative_forecast",
      String(forecastVisible),[["true","Show (not reserved)"],["false","Hide"]]);
    container.append(selectors);
    this.feedback(container);
    const rows=d.slots||[],forecast=forecastVisible?(d.forecast_slots||[]):[];
    const measured=d.actual_slots||[],assumptions=d.forecast_assumptions||{};
    const from=new Date(d.start).getTime(),until=new Date(d.end).getTime();
    const count=Math.max(1,Math.ceil((until-from)/900000));
    const width=820, x0=105, yRows=[28,54,80,106], height=14;
    const scene=mcEl("div");
    const shown=chargers.filter(item=>{
      if(!this._filter)return true;
      if(this._filter==="charger:"+item.id)return true;
      if(!this._filter.startsWith("asset:"))return false;
      const assetId=this._filter.slice(6);
      return item.asset===assetId ||
        [...rows,...forecast,...measured].some(s=>
          s.charger_id===item.id&&s.asset_id===assetId);
    });
    const values=[["proposed_power_kw",rows,"Proposed"],
      ["accepted_power_kw",rows,"Physically accepted"],
      ["actual_power_kw",measured,"Measured physical"],
      ["indicative_power_kw",forecast,"Indicative only"]];
    for(const charger of shown){
      const activeRows=rows.filter(s=>s.charger_id===charger.id);
      const previewRows=forecast.filter(s=>s.charger_id===charger.id);
      const actualRows=measured.filter(s=>s.charger_id===charger.id);
      const selected=cars.find(a=>a.id===charger.asset);
      const hasData=activeRows.length||previewRows.length||actualRows.length;
      const card=mcEl("section","plan-lane");
      const label=mcEl("div","row");
      const historicalAssetId=this._filter.startsWith("asset:")?
        this._filter.slice(6):null;
      const pastOnly=historicalAssetId&&charger.asset!==historicalAssetId;
      const historicAsset=cars.find(a=>a.id===historicalAssetId);
      const vehicleLabel=pastOnly?
        (historicAsset?historicAsset.name:historicalAssetId)+" (historical)":
        selected?selected.name:"No vehicle selected";
      const source=(d.observations||{}).chargers?.[charger.id]?.connected;
      const plugged=source&&source.quality==="ok"?
        source.value?mcTr("Connected")+" · "+mcTr("Vehicle unknown"):mcTr("Disconnected"):mcTr("Connection unknown");
      const fullName=labelMode==="vehicle"?vehicleLabel:
        labelMode==="charger"?charger.name:vehicleLabel+" · "+charger.name;
      const color=colorBy==="charger"?
        mcOwnerColor("charger",charger.id,c,d.plan_palette):
        mcOwnerColor("asset",charger.asset,c,d.plan_palette);
      const lhs=mcEl("div","plan-key");
      const swatch=mcEl("span","plan-swatch");swatch.style.background=color;
      lhs.append(swatch,mcEl("strong","",fullName));
      label.append(lhs,mcEl("span","muted small",plugged));card.append(label);
      if(!hasData){
        card.append(mcEl("p","muted small","No qualified slots for this day."));
      }else{
        const area=mcEl("div","chart");
        const svg=mcSVG("svg",{
          viewBox:"0 0 960 149",class:"timeline",role:"img",
          "aria-label":fullName+" — proposed, accepted, measured and indicative quarter-hour charging"
        });
        const cap=Math.max(0.2,charger.rated_power_kw||0.2,
          ...activeRows.flatMap(s=>[s.proposed_power_kw||0,s.accepted_power_kw||0]),
          ...actualRows.map(s=>s.actual_power_kw||0),
          ...previewRows.map(s=>s.indicative_power_kw||0));
        values.forEach(([key,samples,description],index)=>{
          const y=yRows[index];
          svg.append(mcSVG("text",{x:2,y:y+2},description.replace("Physically accepted","Accepted")
            .replace("Measured physical","Measured").replace("Indicative only","Indicative")));
          svg.append(mcSVG("line",{
            x1:x0,y1:y+7,x2:x0+width,y2:y+7,
            stroke:"currentColor","stroke-opacity":0.15
          }));
          for(const item of samples){
            if(item.charger_id!==charger.id||typeof item[key]!=="number")continue;
            const slotIndex=Math.floor((new Date(item.start).getTime()-from)/900000);
            if(slotIndex<0||slotIndex>=count)continue;
            const kw=item[key];
            const barHeight=Math.max(0,Math.min(height,kw/cap*height));
            const x=x0+slotIndex*width/count;
            const isForecast=key==="indicative_power_kw";
            const isMeasured=key==="actual_power_kw";
            const proven=isMeasured &&
              item.asset_provenance==="confirmed_closed_session"&&item.asset_id;
            const entityColor=colorBy==="charger"?
              mcOwnerColor("charger",charger.id,c,d.plan_palette):
              mcOwnerColor("asset",item.asset_id||charger.asset,c,d.plan_palette);
            const tint=isMeasured&&!proven&&colorBy==="vehicle"?
              "#757d87":entityColor;
            const rect=mcSVG("rect",{
              x,y:y+7-barHeight,
              width:Math.max(1,width/count-0.35),
              height:barHeight,
              fill:isForecast?"none":tint,
              "fill-opacity":key==="proposed_power_kw"?0.4:1,
              stroke:isForecast?tint:"none",
              "stroke-width":isForecast?1.4:0,
              "stroke-dasharray":isForecast?"3 2":"none"
            });
            const name=isMeasured&&!proven?
              charger.name+" · "+mcTr("Vehicle unknown"):
              mcPlanName(item,c,labelMode);
            const caveat=isForecast?" · "+mcTr("Not reserved"):"";
            rect.append(mcSVG("title",{},
              description+" · "+name+" · "+mcTime(item.start,d.timezone)+
              " · "+kw+" kW"+caveat));
            svg.append(rect);
          }
        });
        for(let i=0;i<=4;i++){
          const stamp=new Date(from+(until-from)*i/4);
          svg.append(mcSVG("text",{
            x:x0+i*width/4,y:139,
            "text-anchor":i===0?"start":i===4?"end":"middle"
          },stamp.toLocaleTimeString(undefined,{
            timeZone:d.timezone||"UTC",hour:"2-digit",minute:"2-digit"
          })));
        }
        area.append(svg);card.append(area);
      }
      if(assumptions[charger.id]&&forecastVisible){
        const item=assumptions[charger.id];
        card.append(mcEl("p","plan-caution",mcTr("Indicative")+" · "+
          (item.assumption==="IF_CONNECTED_NOW"?mcTr("If connected now"):
            mcTr("Expected")+" "+mcTime(item.assumed_connection_at,d.timezone))+
          " · "+mcTr("Not reserved")));
      }
      scene.append(card);
    }
    if(!shown.length)this.notice(scene,"No data",false);
    container.append(scene);
    const key=mcEl("div","legend");
    for(const phrase of ["Proposed","Accepted","Measured","Indicative"]){
      key.append(mcEl("span","",phrase));
    }
    container.append(key);
    const groups=Object.entries(assumptions).filter(([id,meta])=>
      forecastVisible&&(!this._filter||this._filter==="charger:"+id||
        this._filter==="asset:"+meta.asset_id));
    if(groups.length){
      const forecastInfo=mcEl("div","card");
      forecastInfo.append(mcEl("h3","",mcTr("Indicative")+" · "+mcTr("Disconnected")));
      for(const [chargerId,meta] of groups){
        const obj=chargers.find(c=>c.id===chargerId);
        const car=cars.find(a=>a.id===meta.asset_id);
        const result=(d.forecast_reasons||{})[chargerId];
        const window=forecast.filter(s=>s.charger_id===chargerId);
        forecastInfo.append(mcEl("p","small",
          (car?car.name:meta.asset_id)+" · "+(obj?obj.name:chargerId)+
          " · "+(window.length?window.length+" × 15 min":mcTr("Unavailable"))+
          (result?" · "+mcReason(result):"")));
      }
      container.append(forecastInfo);
    }
    const prices=(d.price_slots||[]).filter(p=>typeof p.price_per_kwh==="number");
    if(prices.length){
      const currencies=[...new Set(prices.map(p=>p.currency))];
      if(currencies.length===1){
        const lo=Math.min(...prices.map(p=>p.price_per_kwh));
        const hi=Math.max(...prices.map(p=>p.price_per_kwh));
        const range=hi-lo||1;
        const wrapper=mcEl("div","card");
        wrapper.append(mcEl("h3","",mcTr("Tariff")+" · "+currencies[0]+"/kWh"));
        const graph=mcEl("div","chart");
        const svg=mcSVG("svg",{
          viewBox:"0 0 960 72",style:"height:auto",
          role:"img","aria-label":"Qualified energy tariff over actual clock intervals; not confirmed charging costs"
        });
        const x0=105,width=820;
        let path="",lastSlot=-2;
        for(let i=0;i<count;i++){
          const tick=from+i*900000;
          const covered=prices.filter(p=>
            new Date(p.start).getTime()<=tick &&
            new Date(p.end).getTime()>=tick+900000);
          if(covered.length!==1){lastSlot=-2;continue;}
          const x=x0+(i+0.5)*width/count;
          const y=44-(covered[0].price_per_kwh-lo)/range*32;
          path+=(i===lastSlot+1?" L":" M")+x.toFixed(2)+" "+y.toFixed(2);
          lastSlot=i;
        }
        if(path)svg.append(mcSVG("path",{
          d:path,fill:"none",stroke:"#bf8a22","stroke-width":2
        }));
        svg.append(mcSVG("text",{x:2,y:17},String(hi.toFixed(3))));
        svg.append(mcSVG("text",{x:2,y:48},String(lo.toFixed(3))));
        graph.append(svg);wrapper.append(graph);
        wrapper.append(mcEl("p","muted small",
          lo.toFixed(3)+"–"+hi.toFixed(3)+" "+currencies[0]+"/kWh"));
        container.append(wrapper);
      }else{
        this.notice(container,"Unavailable",true);
      }
    }
    if(!measured.some(row=>typeof row.actual_power_kw==="number")){
      this.notice(container,"Measured power unavailable",false);
    }
    const next=mcEl("div","card");
    next.append(mcEl("h3","","Next planned session"));
    const upcoming=rows.filter(s=>typeof s.proposed_power_kw==="number"&&s.proposed_power_kw>0)
      .sort((a,b)=>new Date(a.start)-new Date(b.start))[0];
    next.append(mcEl("p","",upcoming?
      mcPlanName(upcoming,c,labelMode)+" · "+mcTime(upcoming.start,d.timezone)+
      " · "+upcoming.proposed_power_kw+" kW":
      "No active plan"));
    const reasons=Object.entries(d.reasons||{}).filter(([,v])=>v!=="PROPOSED");
    if(reasons.length)next.append(mcEl("p","muted small",
      reasons.map(([k,val])=>k+" · "+mcReason(val)).slice(0,4).join("; ")));
    container.append(next);
  }
  assets(container){
    const d=this._data,assets=d.configuration.assets||[],chargers=d.configuration.chargers||[];
    this.title(container,mcTr("Chargeable Assets")+" ("+assets.length+")");
    if(!assets.length)this.notice(container,"No vehicles",false);
    for(const a of assets){
      const card=mcEl("div","card");const charger=chargers.find(x=>x.asset===a.id);
      const obs=((d.observations||{}).assets||{})[a.id]||{};
      const header=mcEl("div","row");header.append(mcEl("h3","",a.name),mcButton(this._open===a.id?"Hide details":"Details",()=>{this._open=this._open===a.id?"":a.id;this.render();}));
      card.append(header);
      const chip=mcEl("div","plan-key"),dot=mcEl("span","plan-swatch");
      dot.style.background=mcOwnerColor("asset",a.id,d.configuration,d.plan_palette);
      chip.append(dot,mcEl("span","muted small",mcTr("Plan color")+" · "+mcTr(a.plan_color||"blue")));
      card.append(chip);
      const kinds={
        car:"Car",bicycle:"Bicycle",motorcycle:"Motorcycle",scooter:"Scooter",other:"Other"
      };
      mcPair(card,"Asset type",mcTr(kinds[a.kind]||a.kind||"Other"));
      mcPair(card,"Battery",mcValue(obs.soc,"%"));
      mcPair(card,"Effective charging power",mcValue(obs.effective_power_kw," kW"));
      mcPair(card,"Target",a.target_soc===undefined?"Not set":a.target_soc+"%");
      mcPair(card,"Ready By",mcTime(a.ready_by,d.timezone));
      mcPair(card,"Charger",charger?charger.name:"Not assigned");
      if(this._open===a.id){
        const detail=mcEl("div","details");
        mcPair(detail,"Charging priority",a.priority===undefined?"Not set":a.priority);
        mcPair(detail,"Battery data",obs.soc?(obs.soc.quality+" · "+(a.soc_entity||"manual")):"Unknown");
        mcPair(detail,"Requested energy",a.requested_kwh===undefined?"Not set":a.requested_kwh+" kWh");
        mcPair(detail,"Duration",a.requested_duration_minutes===undefined?"Not set":a.requested_duration_minutes+" min");
        this.ownerColorControl(detail,"asset",a);
        for(const [field,label] of [
          ["kind","Asset type"],["target_soc","Target"],["requested_kwh","Requested energy"],
          ["requested_duration_minutes","Duration"],["priority","Priority"],
          ["ready_by","Ready By"],["expected_connection_at","Expected"],
          ["ready_by_repeat","Repeat"]
        ]){
          if(!this.ownerEntity("asset",a.id,field))continue;
          const row=mcEl("div","row");
          row.append(mcEl("span","muted small",label),mcButton("Edit",
            ()=>this.openNative("asset",a.id,field)));
          detail.append(row);
        }
        card.append(detail);
      }
      container.append(card);
    }
    if(this._assetEditor==="new"){
      const form=mcEl("form","card");form.append(mcEl("h3","","Add a chargeable asset"));
      const name=this.field(form,"Asset name","","text");
      const kind=this.field(form,"Asset type","car",null,[
        ["car",mcTr("Car")],["bicycle",mcTr("Bicycle")],
        ["motorcycle",mcTr("Motorcycle")],["scooter",mcTr("Scooter")],
        ["other",mcTr("Other")]
      ]);
      const energy=this.field(form,"Requested energy (kWh)","", "number");
      const temporary=this.field(form,"Temporary guest","yes",null,
        [["yes","Yes — temporary guest"],["no","No — permanent asset"]]);
      const expiry=this.field(form,"Guest expiry ISO time","", "text");
      const arrival=this.field(form,"Expected plug-in time (optional)","", "text");
      form.append(mcButton("Create asset",()=>{
        const id=name.value.trim().toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"");
        const changes={name:name.value.trim(),kind:kind.value};
        if(energy.value!=="")changes.requested_kwh=Number(energy.value);
        if(arrival.value.trim())changes.expected_connection_at=arrival.value.trim();
        if(temporary.value==="yes"){
          changes.temporary=true;changes.expires_at=expiry.value.trim();
        }
        this.saveSettings("asset",id,changes,"create");
      }));
      container.append(form);
    }
    this.feedback(container);
    container.append(mcButton(this._assetEditor==="new"?"Cancel adding":"Add asset",()=>{
      this._assetEditor=this._assetEditor==="new"?"":"new";this.render();
    }));
  }
  chargers(container){
    const d=this._data,chargers=d.configuration.chargers||[],observations=(d.observations||{}).chargers||{};
    this.title(container,mcTr("Chargers")+" ("+chargers.length+")");
    if(!chargers.length)this.notice(container,"No charging points",false);
    for(const c of chargers){
      const obs=observations[c.id]||{};
      const card=mcEl("div","card");
      const head=mcEl("div","row");head.append(mcEl("h3","",c.name),mcButton(this._open===c.id?"Hide details":"Details",()=>{this._open=this._open===c.id?"":c.id;this.render();}));
      card.append(head);
      const chip=mcEl("div","plan-key"),dot=mcEl("span","plan-swatch");
      dot.style.background=mcOwnerColor("charger",c.id,d.configuration,d.plan_palette);
      chip.append(dot,mcEl("span","muted small",mcTr("Plan color")+" · "+mcTr(c.plan_color||"blue")));
      card.append(chip);
      mcPair(card,"Connection",mcValue(obs.connected));
      mcPair(card,"Effective charging power",mcValue(obs.power_kw," kW"));
      mcPair(card,"Control type",c.kind==="on_off"?"On/off":"Variable current");
      const session=(d.active_sessions||{})[c.id];
      if(session){
        mcPair(card,"Active session",mcTime(session.started_at,d.timezone));
        mcPair(card,"Measured session energy",
               session.actual_energy_kwh===null?"Unknown":session.actual_energy_kwh+" kWh");
      }
      mcPair(card,"Assigned asset",c.asset||"Not assigned");
      const identity=(d.connection_identity||{})[c.id]||null;
      const confirmed=(identity&&identity.asset_id===c.asset);
      const selectedAsset=(d.configuration.assets||[]).find(a=>a.id===c.asset);
      mcPair(card,mcTr("Connected vehicle"),confirmed?
        (selectedAsset?selectedAsset.name:c.asset):mcTr("Not confirmed"));
      if(obs.connected?.quality==="ok"&&obs.connected.value===true&&
          c.asset&&!confirmed&&this.ownerEntity("charger",c.id,"confirm_connection")){
        const confirm=mcButton(mcTr("Confirm connected vehicle"),()=>
          this.nativeButton("charger",c.id,"confirm_connection"));
        confirm.disabled=this._settingsBusy;
        card.append(confirm);
      }
      const history=(d.completed_sessions||[]).filter(x=>x.charger_id===c.id);
      const latest=history.length?history[history.length-1]:null;
      if(latest){
        mcPair(card,"Last confirmed session",mcTime(latest.ended_at,d.timezone));
        mcPair(card,"Measured energy",latest.actual_energy_kwh===null?"Unknown":latest.actual_energy_kwh+" kWh");
        mcPair(card,"Verified cost",latest.cost===null?"Unknown":latest.cost+" "+latest.currency);
      }
      if(this._open===c.id){
        const detail=mcEl("div","details");
        mcPair(detail,"Rated power",c.rated_power_kw+" kW");
        mcPair(detail,"Phases",c.phase_count||"Unverified");
        mcPair(detail,"Current range",c.min_current_a&&c.max_current_a?c.min_current_a+"–"+c.max_current_a+" A":"Unknown");
        mcPair(detail,"Source state",obs.power_kw?mcTr(obs.power_kw.quality==="ok"?"Ready":"Unavailable"):"Unknown");
        const actual=(d.command_outcomes||{})[c.id]||{};
        mcPair(detail,"Status",mcTr(actual.status==="confirmed"?"Confirmed":actual.status==="rejected"?"Rejected":actual.status==="execution_unknown"?"Unavailable":"No action"));
        if(actual.reason)mcPair(detail,"Reason",mcReason(actual.reason));
        if(actual.readback_at)mcPair(detail,"Measured confirmation",mcTime(actual.readback_at,d.timezone));
        this.ownerColorControl(detail,"charger",c);
        if(this.ownerEntity("charger",c.id,"asset")){
          const setting=mcEl("div","row");
          setting.append(mcEl("span","muted small","Selected vehicle"),
            mcButton("Edit",()=>this.openNative("charger",c.id,"asset")));
          detail.append(setting);
        }
        card.append(detail);
      }
      const capability=(d.command_capabilities||{})[c.id]||{};
      const outcome=this._commandFeedback[c.id]||(d.command_outcomes||{})[c.id];
      const controls=mcEl("div","controls");
      if(capability.start_allowed){
        const start=mcButton("Start charging",()=>this.command(c.id,"start"));
        start.disabled=this._commandBusy;
        controls.append(start);
      }
      if(capability.stop_allowed){
        const stop=mcButton("Stop charging",()=>this.command(c.id,"stop"));
        stop.disabled=this._commandBusy;
        controls.append(stop);
      }
      if(controls.children.length)card.append(controls);
      if(!capability.start_allowed && capability.reason)
        card.append(mcEl("p","muted small",mcTr("Unavailable")+" · "+mcReason(capability.reason)));
      if(outcome){
        const bad=outcome.status==="rejected"||outcome.status==="execution_unknown";
        const label=bad?mcReason(outcome.reason):outcome.status==="confirmed"?
          (outcome.action==="stop"?"Stopped":"Charging"):"Pending";
        const status=mcEl("p","small"+(bad?" error":""),label);
        status.setAttribute("role",bad?"alert":"status");
        card.append(status);
      }
      container.append(card);
    }
    container.append(mcButton("Add charger",()=>this.settingsSelect(container,"Sources & bindings")));
  }
  settings(container){
    const d=this._data,c=d.configuration||{},ctl=c.controller||{};
    this.title(container,"Settings");

    this.configure(container);
    this.feedback(container);
    for(const title of MC_SETTINGS){
      const group=mcEl("section","card"),open=title===this._settingsOpen;
      const row=mcEl("div","row");
      row.append(mcEl("h3","",title),mcButton(open?"Close":"Edit",()=>{
        this._settingsOpen=open?"":title;this.render();
      }));
      group.append(row);
      if(open){
        const detail=mcEl("div","details");
        if(title==="Charging site"){
          mcPair(detail,"Site name",ctl.name);
          for(const field of ["max_parallel","max_power_kw"]){
            if(!this.ownerEntity("controller",ctl.id,field))continue;
            const item=mcEl("div","row");
            item.append(mcEl("span","",field==="max_parallel"?"Parallel chargers":"Maximum group kW"),
              mcButton("Edit",()=>this.openNative("controller",ctl.id,field)));
            detail.append(item);
          }
        }else if(title==="Charging strategy"){
          const options=mcEl("div","chips");
          for(const mode of MC_MODES){
            const btn=mcButton(mode,()=>this.nativeSelect("controller",ctl.id,"mode",mode));
            btn.disabled=this._settingsBusy||mode===ctl.mode||
              !this.ownerEntity("controller",ctl.id,"mode");
            if(mode===ctl.mode)btn.className="active";
            options.append(btn);
          }
          detail.append(options);
        }else if(title==="Integrations"){
          mcPair(detail,"Tariff",mcReason((d.observations||{}).sources?.tariff_quality));
          mcPair(detail,"Solar",mcReason((d.observations||{}).sources?.solar_quality));
          mcPair(detail,"Capacity",mcReason((d.observations||{}).sources?.binding_quality));
        }else if(title==="Safety & limits"){
          mcPair(detail,"Maximum group kW",ctl.max_power_kw===undefined?
            "Unknown":ctl.max_power_kw+" kW");
          this.configure(detail);
        }else{
          this.configure(detail);
        }
        group.append(detail);
      }
      container.append(group);
    }
  }
}
if(!customElements.get("robotix-multicharge-card"))customElements.define("robotix-multicharge-card",RobotixMultiChargeCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==="robotix-multicharge-card")){
  window.customCards.push({type:"robotix-multicharge-card",name:"Robotix MultiCharge",description:"Charging plan"});
}