/* Robotix MultiCharge native Home Assistant card: one backend, five honest views. */
let mcLanguage="en";
const MC_TEXT={"nl":{"Overview":"Overzicht","Charging Plan":"Laadplan","Chargeable Assets":"Voertuigen","Chargers":"Laadpalen","Settings":"Instellingen","Charging plan":"Laadplan","Charging overview":"Laadoverzicht","Refresh":"Vernieuwen","Today":"Vandaag","Tomorrow":"Morgen","All chargers":"Alle laadpalen","Show labels":"Toon","Color by":"Kleur per","Indicative forecasting":"Prognose","Vehicle":"Voertuig","Charger":"Laadpaal","Vehicle + Charger":"Voertuig + laadpaal","Show (not reserved)":"Tonen","Hide":"Verbergen","Proposed":"Voorgesteld","Accepted":"Bevestigd","Measured":"Gemeten","Indicative":"Indicatief","No vehicle selected":"Geen voertuig","Connected":"Aangesloten","Disconnected":"Niet aangesloten","Connection unknown":"Aansluiting onbekend","Vehicle unknown":"Voertuig onbekend","Unavailable":"Niet beschikbaar","Unknown":"Onbekend","Not set":"Niet ingesteld","Not assigned":"Niet toegewezen","Plan color":"Plankleur","Plan labels":"Planlabels","Active chargers":"Actieve laadpalen","Actual power":"Werkelijk vermogen","Current price":"Huidig tarief","Charging strategy":"Laadmodus","Charging site":"Laadlocatie","Solar production":"Zonneproductie","Home consumption":"Woningverbruik","Grid power":"Netvermogen","Solar surplus":"Zonne-overschot","Future tariff intervals":"Toekomstige tariefintervallen","Current import price":"Huidig aankoopttarief","Current export price":"Huidige injectievergoeding","Solar intervals":"Zonintervallen","Available surplus":"Beschikbaar overschot","Solar source":"Zonnebron","Grid direction":"Netrichting","Sources & bindings":"Bronnen","Safety & limits":"Veiligheid en limieten","Integrations":"Integraties","Advanced & YAML":"Geavanceerd","Readiness":"Gereedheid","Battery":"Batterij","Target":"Doel","Ready By":"Klaar om","Priority":"Prioriteit","Duration":"Duur","Requested energy":"Gevraagde energie","Charging intention":"Laadbehoefte","Charging priority":"Prioriteit","Connection":"Aansluiting","Selected vehicle":"Gekozen voertuig","Assigned asset":"Gekozen voertuig","Actual current":"Gemeten stroom","Power":"Vermogen","Source state":"Bronstatus","Status":"Status","Start charging":"Start laden","Stop charging":"Stop laden","Details":"Details","Hide details":"Sluiten","Edit":"Wijzigen","Saved":"Opgeslagen","Pending":"In behandeling","Rejected":"Geweigerd","Next planned session":"Volgende laadsessie","Next action":"Volgende stap","No active qualified vehicle plan":"Geen actieve planning","No qualified slots for this day.":"Geen laadmomenten","No vehicles":"Geen voertuigen","No charging points":"Geen laadpalen","Loading":"Laden","Error":"Fout","No data":"Geen gegevens","No connection":"Niet aangesloten","Not ready":"Niet gereed","Waiting":"Wachten","Forecast":"Prognose","If connected now":"Bij nu aansluiten","Expected":"Verwacht","Not reserved":"Niet gereserveerd","Measured power unavailable":"Geen meetgegevens","Vehicle plan":"Voertuigplan","Charger plan":"Laadpaalplan","No forecast":"Geen prognose","No vehicle":"Geen voertuig","Tariff":"Tarief","Proposed · pale color":"Voorgesteld","Accepted · solid color":"Geaccepteerd","Measured · physical source":"Gemeten","Indicative · dashed outline":"Indicatief","Add asset":"Voertuig toevoegen","Add charger":"Laadpaal toevoegen","Charging mode":"Laadmodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blauw","orange":"Oranje","green":"Groen","purple":"Paars","gold":"Goud","teal":"Blauwgroen","pink":"Roze","indigo":"Indigo","olive":"Olijfgroen","brown":"Bruin","coral":"Koraal","slate":"Leigrijs","violet":"Violet","lime":"Limoen","salmon":"Zalm","cyan":"Cyaan","wine":"Wijnrood","forest":"Bosgroen","peach":"Perzik","lavender":"Lavendel","turquoise":"Turkoois","rust":"Roest","navy":"Marineblauw","moss":"Mosgroen","Guest expired":"Gast verlopen","Ready":"Gereed","No tariff":"Geen tarief","No solar":"Geen zon","No deadline":"Geen eindtijd","No charging goal":"Geen laaddoel","Limited power":"Beperkt vermogen","No source":"Geen bron","No capacity":"Geen capaciteit","Wiring unknown":"Aansluiting onbekend","Guest":"Gast","Charged":"Geladen","Charging":"Laden","Stopped":"Gestopt","Confirmed":"Bevestigd","No action":"Geen actie","Reason":"Reden","Energy":"Energie","Repeat":"Herhalen","Measured session energy":"Sessie-energie","Last confirmed session":"Laatste sessie","Measured energy":"Gemeten energie","Verified cost":"Kosten","Current range":"Stroomsterkte","Measured confirmation":"Gemeten om","Control type":"Sturing","On/off":"Aan/uit","Variable current":"Variabele stroom","Unverified":"Onbekend","No charger assigned":"Geen laadpaal","Target battery %":"Doelbatterij %","Asset name":"Voertuignaam","Asset type":"Soort","Temporary guest":"Tijdelijke gast","Guest until":"Gast tot","Expected connection":"Verwachte aansluiting","Save charging site":"Laadlocatie opslaan","Save sources":"Bronnen opslaan","Maximum group kW":"Max. vermogen kW","Group power ceiling kW":"Max. vermogen kW","Site name":"Locatienaam","Parallel chargers":"Gelijktijdige laders","Save electrical limits":"Limieten opslaan","Electrical limits":"Limieten","Battery data":"Batterijbron","Rated power":"Nominaal vermogen","Phases":"Fasen","Active session":"Actieve sessie","Add a chargeable asset":"Voertuig toevoegen","Create asset":"Toevoegen","Cancel adding":"Annuleren","Remove":"Verwijderen","Effective charging power":"Effectief laadvermogen","Car":"Auto","Bicycle":"Fiets","Motorcycle":"Motorfiets","Scooter":"Scooter","Other":"Overig","No active plan":"Geen actieve planning","Confirm connected vehicle":"Bevestig aangesloten voertuig","Connected vehicle":"Aangesloten voertuig","Not confirmed":"Niet bevestigd"},"fr":{"Overview":"Vue d’ensemble","Charging Plan":"Plan de charge","Chargeable Assets":"Véhicules","Chargers":"Bornes","Settings":"Réglages","Charging plan":"Plan de charge","Charging overview":"Vue des charges","Refresh":"Actualiser","Today":"Aujourd’hui","Tomorrow":"Demain","All chargers":"Toutes les bornes","Show labels":"Afficher","Color by":"Couleur par","Indicative forecasting":"Prévision","Vehicle":"Véhicule","Charger":"Borne","Vehicle + Charger":"Véhicule + borne","Show (not reserved)":"Afficher","Hide":"Masquer","Proposed":"Proposé","Accepted":"Confirmé","Measured":"Mesuré","Indicative":"Indicatif","No vehicle selected":"Aucun véhicule","Connected":"Connecté","Disconnected":"Déconnecté","Connection unknown":"Connexion inconnue","Vehicle unknown":"Véhicule inconnu","Unavailable":"Indisponible","Unknown":"Inconnu","Not set":"Non défini","Not assigned":"Non attribué","Plan color":"Couleur du plan","Plan labels":"Libellés du plan","Active chargers":"Bornes actives","Actual power":"Puissance réelle","Current price":"Tarif actuel","Charging strategy":"Mode de charge","Charging site":"Site de recharge","Solar production":"Production solaire","Home consumption":"Consommation du logement","Grid power":"Puissance du réseau","Solar surplus":"Surplus solaire","Future tariff intervals":"Intervalles futurs de prix","Current import price":"Prix d'achat actuel","Current export price":"Prix de vente actuel","Solar intervals":"Intervalles solaires","Available surplus":"Surplus disponible","Solar source":"Source solaire","Grid direction":"Sens du réseau","Sources & bindings":"Sources","Safety & limits":"Sécurité et limites","Integrations":"Intégrations","Advanced & YAML":"Avancé","Readiness":"Disponibilité","Battery":"Batterie","Target":"Cible","Ready By":"Prêt pour","Priority":"Priorité","Duration":"Durée","Requested energy":"Énergie demandée","Charging intention":"Besoin de charge","Charging priority":"Priorité","Connection":"Connexion","Selected vehicle":"Véhicule choisi","Assigned asset":"Véhicule choisi","Actual current":"Courant réel","Power":"Puissance","Source state":"État de la source","Status":"État","Start charging":"Démarrer","Stop charging":"Arrêter","Details":"Détails","Hide details":"Fermer","Edit":"Modifier","Saved":"Enregistré","Pending":"En attente","Rejected":"Refusé","Next planned session":"Prochaine charge","Next action":"Prochaine étape","No active qualified vehicle plan":"Aucune charge prévue","No qualified slots for this day.":"Aucun créneau","No vehicles":"Aucun véhicule","No charging points":"Aucune borne","Loading":"Chargement","Error":"Erreur","No data":"Aucune donnée","No connection":"Déconnecté","Not ready":"Non prêt","Waiting":"En attente","Forecast":"Prévision","If connected now":"Si connecté maintenant","Expected":"Prévu","Not reserved":"Non réservé","Measured power unavailable":"Mesure indisponible","Vehicle plan":"Plan véhicule","Charger plan":"Plan borne","No forecast":"Aucune prévision","No vehicle":"Aucun véhicule","Tariff":"Tarif","Proposed · pale color":"Proposé","Accepted · solid color":"Accepté","Measured · physical source":"Mesuré","Indicative · dashed outline":"Indicatif","Add asset":"Ajouter un véhicule","Add charger":"Ajouter borne","Charging mode":"Mode de charge","Mode":"Mode","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Bleu","orange":"Orange","green":"Vert","purple":"Violet","gold":"Or","teal":"Sarcelle","pink":"Rose","indigo":"Indigo","olive":"Olive","brown":"Marron","coral":"Corail","slate":"Ardoise","violet":"Mauve","lime":"Citron vert","salmon":"Saumon","cyan":"Cyan","wine":"Bordeaux","forest":"Vert forêt","peach":"Pêche","lavender":"Lavande","turquoise":"Turquoise","rust":"Rouille","navy":"Bleu marine","moss":"Vert mousse","Guest expired":"Invité expiré","Ready":"Prêt","No tariff":"Aucun tarif","No solar":"Pas de solaire","No deadline":"Pas d’échéance","No charging goal":"Aucune cible","Limited power":"Puissance limitée","No source":"Aucune source","No capacity":"Pas de capacité","Wiring unknown":"Câblage inconnu","Guest":"Invité","Charged":"Chargé","Charging":"Recharge","Stopped":"Arrêté","Confirmed":"Confirmé","No action":"Aucune action","Reason":"Motif","Energy":"Énergie","Repeat":"Répéter","Measured session energy":"Énergie de session","Last confirmed session":"Dernière session","Measured energy":"Énergie mesurée","Verified cost":"Coût","Current range":"Plage de courant","Measured confirmation":"Mesuré à","Control type":"Commande","On/off":"Marche/arrêt","Variable current":"Courant variable","Unverified":"Inconnu","No charger assigned":"Aucune borne","Target battery %":"Batterie cible %","Asset name":"Nom du véhicule","Asset type":"Type","Temporary guest":"Invité temporaire","Guest until":"Invité jusqu’à","Expected connection":"Connexion prévue","Save charging site":"Enregistrer le site","Save sources":"Enregistrer les sources","Maximum group kW":"Puissance max. kW","Group power ceiling kW":"Puissance max. kW","Site name":"Nom du site","Parallel chargers":"Bornes simultanées","Save electrical limits":"Enregistrer les limites","Electrical limits":"Limites","Battery data":"Source batterie","Rated power":"Puissance nominale","Phases":"Phases","Active session":"Session active","Add a chargeable asset":"Ajouter un véhicule","Create asset":"Ajouter","Cancel adding":"Annuler","Remove":"Supprimer","Effective charging power":"Puissance de charge effective","Car":"Voiture","Bicycle":"Vélo","Motorcycle":"Moto","Scooter":"Trottinette","Other":"Autre","No active plan":"Aucune charge planifiée","Confirm connected vehicle":"Confirmer le véhicule branché","Connected vehicle":"Véhicule branché","Not confirmed":"Non confirmé"},"da":{"Overview":"Overblik","Charging Plan":"Ladeplan","Chargeable Assets":"Køretøjer","Chargers":"Ladere","Settings":"Indstillinger","Charging plan":"Ladeplan","Charging overview":"Ladeoversigt","Refresh":"Opdater","Today":"I dag","Tomorrow":"I morgen","All chargers":"Alle ladere","Show labels":"Vis etiketter","Color by":"Farve efter","Indicative forecasting":"Prognose","Vehicle":"Køretøj","Charger":"Lader","Vehicle + Charger":"Køretøj + lader","Show (not reserved)":"Vis","Hide":"Skjul","Proposed":"Foreslået","Accepted":"Accepteret","Measured":"Målt","Indicative":"Vejledende","No vehicle selected":"Intet køretøj valgt","Connected":"Tilsluttet","Disconnected":"Ikke tilsluttet","Connection unknown":"Tilslutning ukendt","Vehicle unknown":"Køretøj ukendt","Unavailable":"Ikke tilgængelig","Unknown":"Ukendt","Not set":"Ikke angivet","Not assigned":"Ikke tildelt","Plan color":"Planfarve","Plan labels":"Planetiketter","Active chargers":"Aktive ladere","Actual power":"Aktuel effekt","Current price":"Aktuel pris","Charging strategy":"Ladetilstand","Charging site":"Ladested","Sources & bindings":"Kilder","Safety & limits":"Sikkerhed og grænser","Integrations":"Integrationer","Advanced & YAML":"Avanceret","Readiness":"Klar","Battery":"Batteri","Target":"Mål","Ready By":"Klar kl.","Priority":"Prioritet","Duration":"Varighed","Requested energy":"Ønsket energi","Charging intention":"Ladebehov","Charging priority":"Ladeprioritet","Connection":"Tilslutning","Selected vehicle":"Valgt køretøj","Assigned asset":"Tildelt køretøj","Actual current":"Aktuel strøm","Power":"Effekt","Source state":"Kildestatus","Status":"Status","Start charging":"Start opladning","Stop charging":"Stop opladning","Details":"Detaljer","Hide details":"Skjul detaljer","Edit":"Rediger","Saved":"Gemt","Pending":"Afventer","Rejected":"Afvist","Next planned session":"Næste planlagte opladning","Next action":"Næste handling","No active qualified vehicle plan":"Ingen aktiv ladeplan","No qualified slots for this day.":"Ingen ladetider","No vehicles":"Ingen køretøjer","No charging points":"Ingen ladere","Loading":"Indlæser","Error":"Fejl","No data":"Ingen data","No connection":"Ikke tilsluttet","Not ready":"Ikke klar","Waiting":"Venter","Forecast":"Prognose","If connected now":"Hvis tilsluttet nu","Expected":"Forventet","Not reserved":"Ikke reserveret","Measured power unavailable":"Ingen måledata","Vehicle plan":"Køretøjsplan","Charger plan":"Ladeplan","No forecast":"Ingen prognose","No vehicle":"Intet køretøj","Tariff":"Tarif","Proposed · pale color":"Foreslået","Accepted · solid color":"Accepteret","Measured · physical source":"Målt","Indicative · dashed outline":"Vejledende","Add asset":"Tilføj køretøj","Add charger":"Tilføj lader","Charging mode":"Ladetilstand","Mode":"Tilstand","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Orange","green":"Grøn","purple":"Lilla","gold":"Guld","teal":"Blågrøn","pink":"Pink","indigo":"Indigo","olive":"Oliven","brown":"Brun","coral":"Koral","slate":"Skifer","violet":"Violet","lime":"Lime","salmon":"Laks","cyan":"Cyan","wine":"Vinrød","forest":"Skovgrøn","peach":"Fersken","lavender":"Lavendel","turquoise":"Turkis","rust":"Rust","navy":"Marineblå","moss":"Mosgrøn","Guest expired":"Gæst udløbet","Ready":"Klar","No tariff":"Ingen tarif","No solar":"Ingen sol","No deadline":"Ingen frist","No charging goal":"Intet lademål","Limited power":"Begrænset effekt","No source":"Ingen kilde","No capacity":"Ingen kapacitet","Wiring unknown":"Ukendt ledningsføring","Guest":"Gæst","Charged":"Opladet","Charging":"Oplader","Stopped":"Stoppet","Confirmed":"Bekræftet","No action":"Ingen handling","Reason":"Årsag","Energy":"Energi","Repeat":"Gentag","Measured session energy":"Målt sessionsenergi","Last confirmed session":"Sidste session","Measured energy":"Målt energi","Verified cost":"Bekræftet pris","Current range":"Strømområde","Measured confirmation":"Målt kl.","Control type":"Styringstype","On/off":"Til/fra","Variable current":"Variabel strøm","Unverified":"Ikke verificeret","No charger assigned":"Ingen lader valgt","Target battery %":"Målbatteri %","Asset name":"Køretøjsnavn","Asset type":"Køretøjstype","Temporary guest":"Midlertidig gæst","Guest until":"Gæst indtil","Expected connection":"Forventet tilslutning","Save charging site":"Gem ladested","Save sources":"Gem kilder","Maximum group kW":"Maks. effekt kW","Group power ceiling kW":"Effektgrænse kW","Site name":"Stedsnavn","Parallel chargers":"Samtidige ladere","Save electrical limits":"Gem elektriske grænser","Electrical limits":"Elektriske grænser","Battery data":"Batterikilde","Rated power":"Nominel effekt","Phases":"Faser","Active session":"Aktiv session","Add a chargeable asset":"Tilføj køretøj","Create asset":"Opret køretøj","Cancel adding":"Annuller","Remove":"Fjern","Effective charging power":"Effektiv ladeeffekt","Car":"Bil","Bicycle":"Cykel","Motorcycle":"Motorcykel","Scooter":"Scooter","Other":"Andet","No active plan":"Ingen aktiv ladeplan","Confirm connected vehicle":"Bekræft tilsluttet køretøj","Connected vehicle":"Tilsluttet køretøj","Not confirmed":"Ikke bekræftet"},"nb":{"Overview":"Oversikt","Charging Plan":"Ladeplan","Chargeable Assets":"Kjøretøy","Chargers":"Ladere","Settings":"Innstillinger","Charging plan":"Ladeplan","Charging overview":"Ladeoversikt","Refresh":"Oppdater","Today":"I dag","Tomorrow":"I morgen","All chargers":"Alle ladere","Show labels":"Vis etiketter","Color by":"Farge etter","Indicative forecasting":"Prognose","Vehicle":"Kjøretøy","Charger":"Lader","Vehicle + Charger":"Kjøretøy + lader","Show (not reserved)":"Vis","Hide":"Skjul","Proposed":"Foreslått","Accepted":"Godkjent","Measured":"Målt","Indicative":"Veiledende","No vehicle selected":"Ingen kjøretøy valgt","Connected":"Tilkoblet","Disconnected":"Ikke tilkoblet","Connection unknown":"Tilkobling ukjent","Vehicle unknown":"Kjøretøy ukjent","Unavailable":"Ikke tilgjengelig","Unknown":"Ukjent","Not set":"Ikke angitt","Not assigned":"Ikke tilordnet","Plan color":"Planfarge","Plan labels":"Planetiketter","Active chargers":"Aktive ladere","Actual power":"Faktisk effekt","Current price":"Gjeldende pris","Charging strategy":"Lademodus","Charging site":"Ladested","Sources & bindings":"Kilder","Safety & limits":"Sikkerhet og grenser","Integrations":"Integrasjoner","Advanced & YAML":"Avansert","Readiness":"Klar","Battery":"Batteri","Target":"Mål","Ready By":"Klar innen","Priority":"Prioritet","Duration":"Varighet","Requested energy":"Ønsket energi","Charging intention":"Ladebehov","Charging priority":"Ladeprioritet","Connection":"Tilkobling","Selected vehicle":"Valgt kjøretøy","Assigned asset":"Tilordnet kjøretøy","Actual current":"Faktisk strøm","Power":"Effekt","Source state":"Kildestatus","Status":"Status","Start charging":"Start lading","Stop charging":"Stopp lading","Details":"Detaljer","Hide details":"Skjul detaljer","Edit":"Rediger","Saved":"Lagret","Pending":"Venter","Rejected":"Avvist","Next planned session":"Neste planlagte lading","Next action":"Neste handling","No active qualified vehicle plan":"Ingen aktiv ladeplan","No qualified slots for this day.":"Ingen ladetider","No vehicles":"Ingen kjøretøy","No charging points":"Ingen ladere","Loading":"Laster","Error":"Feil","No data":"Ingen data","No connection":"Ikke tilkoblet","Not ready":"Ikke klar","Waiting":"Venter","Forecast":"Prognose","If connected now":"Hvis tilkoblet nå","Expected":"Forventet","Not reserved":"Ikke reservert","Measured power unavailable":"Ingen måledata","Vehicle plan":"Kjøretøyplan","Charger plan":"Ladeplan","No forecast":"Ingen prognose","No vehicle":"Ingen kjøretøy","Tariff":"Pris","Proposed · pale color":"Foreslått","Accepted · solid color":"Godkjent","Measured · physical source":"Målt","Indicative · dashed outline":"Veiledende","Add asset":"Legg til kjøretøy","Add charger":"Legg til lader","Charging mode":"Lademodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Oransje","green":"Grønn","purple":"Lilla","gold":"Gull","teal":"Blågrønn","pink":"Rosa","indigo":"Indigo","olive":"Oliven","brown":"Brun","coral":"Korall","slate":"Skifer","violet":"Fiolett","lime":"Lime","salmon":"Laks","cyan":"Cyan","wine":"Vinrød","forest":"Skoggrønn","peach":"Fersken","lavender":"Lavendel","turquoise":"Turkis","rust":"Rust","navy":"Marineblå","moss":"Mosegrønn","Guest expired":"Gjest utløpt","Ready":"Klar","No tariff":"Ingen pris","No solar":"Ingen sol","No deadline":"Ingen frist","No charging goal":"Ingen lademål","Limited power":"Begrenset effekt","No source":"Ingen kilde","No capacity":"Ingen kapasitet","Wiring unknown":"Ukjent kabling","Guest":"Gjest","Charged":"Ladet","Charging":"Lader","Stopped":"Stoppet","Confirmed":"Bekreftet","No action":"Ingen handling","Reason":"Årsak","Energy":"Energi","Repeat":"Gjenta","Measured session energy":"Målt øktenergi","Last confirmed session":"Siste økt","Measured energy":"Målt energi","Verified cost":"Bekreftet kostnad","Current range":"Strømområde","Measured confirmation":"Målt kl.","Control type":"Styringstype","On/off":"Av/på","Variable current":"Variabel strøm","Unverified":"Ikke verifisert","No charger assigned":"Ingen lader valgt","Target battery %":"Batterimål %","Asset name":"Kjøretøynavn","Asset type":"Kjøretøytype","Temporary guest":"Midlertidig gjest","Guest until":"Gjest til","Expected connection":"Forventet tilkobling","Save charging site":"Lagre ladested","Save sources":"Lagre kilder","Maximum group kW":"Maks. effekt kW","Group power ceiling kW":"Effektgrense kW","Site name":"Stedsnavn","Parallel chargers":"Samtidige ladere","Save electrical limits":"Lagre grenser","Electrical limits":"Elektriske grenser","Battery data":"Batterikilde","Rated power":"Nominell effekt","Phases":"Faser","Active session":"Aktiv økt","Add a chargeable asset":"Legg til kjøretøy","Create asset":"Opprett kjøretøy","Cancel adding":"Avbryt","Remove":"Fjern","Effective charging power":"Effektiv ladeeffekt","Car":"Bil","Bicycle":"Sykkel","Motorcycle":"Motorsykkel","Scooter":"Sparkesykkel","Other":"Annet","No active plan":"Ingen aktiv ladeplan","Confirm connected vehicle":"Bekreft tilkoblet kjøretøy","Connected vehicle":"Tilkoblet kjøretøy","Not confirmed":"Ikke bekreftet"},"sv":{"Overview":"Översikt","Charging Plan":"Laddplan","Chargeable Assets":"Fordon","Chargers":"Laddare","Settings":"Inställningar","Charging plan":"Laddplan","Charging overview":"Laddöversikt","Refresh":"Uppdatera","Today":"I dag","Tomorrow":"I morgon","All chargers":"Alla laddare","Show labels":"Visa etiketter","Color by":"Färg efter","Indicative forecasting":"Prognos","Vehicle":"Fordon","Charger":"Laddare","Vehicle + Charger":"Fordon + laddare","Show (not reserved)":"Visa","Hide":"Dölj","Proposed":"Föreslaget","Accepted":"Godkänt","Measured":"Mätt","Indicative":"Preliminärt","No vehicle selected":"Inget fordon valt","Connected":"Ansluten","Disconnected":"Inte ansluten","Connection unknown":"Anslutning okänd","Vehicle unknown":"Fordon okänt","Unavailable":"Inte tillgänglig","Unknown":"Okänd","Not set":"Inte angiven","Not assigned":"Inte tilldelad","Plan color":"Planfärg","Plan labels":"Planetiketter","Active chargers":"Aktiva laddare","Actual power":"Faktisk effekt","Current price":"Aktuellt pris","Charging strategy":"Laddläge","Charging site":"Laddplats","Sources & bindings":"Källor","Safety & limits":"Säkerhet och gränser","Integrations":"Integrationer","Advanced & YAML":"Avancerat","Readiness":"Redo","Battery":"Batteri","Target":"Mål","Ready By":"Klar senast","Priority":"Prioritet","Duration":"Varaktighet","Requested energy":"Önskad energi","Charging intention":"Laddbehov","Charging priority":"Laddprioritet","Connection":"Anslutning","Selected vehicle":"Valt fordon","Assigned asset":"Tilldelat fordon","Actual current":"Faktisk ström","Power":"Effekt","Source state":"Källstatus","Status":"Status","Start charging":"Starta laddning","Stop charging":"Stoppa laddning","Details":"Detaljer","Hide details":"Dölj detaljer","Edit":"Ändra","Saved":"Sparat","Pending":"Väntar","Rejected":"Avvisat","Next planned session":"Nästa planerade laddning","Next action":"Nästa åtgärd","No active qualified vehicle plan":"Ingen aktiv laddplan","No qualified slots for this day.":"Inga laddtider","No vehicles":"Inga fordon","No charging points":"Inga laddare","Loading":"Läser in","Error":"Fel","No data":"Inga data","No connection":"Inte ansluten","Not ready":"Inte redo","Waiting":"Väntar","Forecast":"Prognos","If connected now":"Om ansluten nu","Expected":"Förväntad","Not reserved":"Inte reserverad","Measured power unavailable":"Inga mätdata","Vehicle plan":"Fordonsplan","Charger plan":"Laddplan","No forecast":"Ingen prognos","No vehicle":"Inget fordon","Tariff":"Pris","Proposed · pale color":"Föreslaget","Accepted · solid color":"Godkänt","Measured · physical source":"Mätt","Indicative · dashed outline":"Preliminärt","Add asset":"Lägg till fordon","Add charger":"Lägg till laddare","Charging mode":"Laddläge","Mode":"Läge","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Orange","green":"Grön","purple":"Lila","gold":"Guld","teal":"Blågrön","pink":"Rosa","indigo":"Indigo","olive":"Oliv","brown":"Brun","coral":"Korall","slate":"Skiffer","violet":"Violett","lime":"Lime","salmon":"Lax","cyan":"Cyan","wine":"Vinröd","forest":"Skogsgrön","peach":"Persika","lavender":"Lavendel","turquoise":"Turkos","rust":"Rost","navy":"Marinblå","moss":"Mossgrön","Guest expired":"Gäst utgången","Ready":"Redo","No tariff":"Inget pris","No solar":"Ingen sol","No deadline":"Ingen tidsgräns","No charging goal":"Inget laddmål","Limited power":"Begränsad effekt","No source":"Ingen källa","No capacity":"Ingen kapacitet","Wiring unknown":"Okänd ledning","Guest":"Gäst","Charged":"Laddad","Charging":"Laddar","Stopped":"Stoppad","Confirmed":"Bekräftad","No action":"Ingen åtgärd","Reason":"Orsak","Energy":"Energi","Repeat":"Upprepa","Measured session energy":"Uppmätt sessionsenergi","Last confirmed session":"Senaste session","Measured energy":"Uppmätt energi","Verified cost":"Bekräftad kostnad","Current range":"Strömområde","Measured confirmation":"Mätt kl.","Control type":"Styrningstyp","On/off":"På/av","Variable current":"Variabel ström","Unverified":"Inte verifierad","No charger assigned":"Ingen laddare vald","Target battery %":"Batterimål %","Asset name":"Fordonsnamn","Asset type":"Fordonstyp","Temporary guest":"Tillfällig gäst","Guest until":"Gäst till","Expected connection":"Förväntad anslutning","Save charging site":"Spara laddplats","Save sources":"Spara källor","Maximum group kW":"Max. effekt kW","Group power ceiling kW":"Effektgräns kW","Site name":"Platsnamn","Parallel chargers":"Samtidiga laddare","Save electrical limits":"Spara gränser","Electrical limits":"Elektriska gränser","Battery data":"Batterikälla","Rated power":"Nominell effekt","Phases":"Faser","Active session":"Aktiv session","Add a chargeable asset":"Lägg till fordon","Create asset":"Skapa fordon","Cancel adding":"Avbryt","Remove":"Ta bort","Effective charging power":"Effektiv laddeffekt","Car":"Bil","Bicycle":"Cykel","Motorcycle":"Motorcykel","Scooter":"Elsparkcykel","Other":"Annat","No active plan":"Ingen aktiv laddplan","Confirm connected vehicle":"Bekräfta anslutet fordon","Connected vehicle":"Anslutet fordon","Not confirmed":"Inte bekräftat"},"de":{"Overview":"Übersicht","Charging Plan":"Ladeplan","Chargeable Assets":"Lade-Assets","Chargers":"Ladepunkte","Settings":"Einstellungen","Charging plan":"Ladeplan","Charging overview":"Ladeübersicht","Refresh":"Aktualisieren","Today":"Heute","Tomorrow":"Morgen","All chargers":"Alle Ladepunkte","Show labels":"Beschriftung","Color by":"Farbe nach","Indicative forecasting":"Prognose","Vehicle":"Asset","Charger":"Ladepunkt","Vehicle + Charger":"Asset + Ladepunkt","Show (not reserved)":"Anzeigen","Hide":"Ausblenden","Proposed":"Vorgeschlagen","Accepted":"Angenommen","Measured":"Gemessen","Indicative":"Unverbindlich","No vehicle selected":"Kein Asset gewählt","Connected":"Verbunden","Disconnected":"Nicht verbunden","Connection unknown":"Verbindung unbekannt","Vehicle unknown":"Asset unbekannt","Unavailable":"Nicht verfügbar","Unknown":"Unbekannt","Not set":"Nicht festgelegt","Not assigned":"Nicht zugewiesen","Plan color":"Planfarbe","Plan labels":"Planbeschriftung","Active chargers":"Aktive Ladepunkte","Actual power":"Ist-Leistung","Current price":"Aktueller Preis","Charging strategy":"Lademodus","Charging site":"Ladestandort","Solar production":"Solarproduktion","Home consumption":"Hausverbrauch","Grid power":"Netzleistung","Solar surplus":"Solarüberschuss","Future tariff intervals":"Zukünftige Preisintervalle","Current import price":"Aktueller Bezugspreis","Current export price":"Aktueller Einspeisepreis","Solar intervals":"Solarintervalle","Available surplus":"Verfügbarer Überschuss","Solar source":"Solarquelle","Grid direction":"Netzrichtung","Sources & bindings":"Quellen und Zuordnung","Safety & limits":"Sicherheit und Grenzen","Integrations":"Integrationen","Advanced & YAML":"Erweitert","Readiness":"Bereitschaft","Battery":"Batterie","Target":"Ziel","Ready By":"Bereit bis","Priority":"Priorität","Duration":"Dauer","Requested energy":"Energiebedarf","Charging intention":"Ladebedarf","Charging priority":"Ladepriorität","Connection":"Verbindung","Selected vehicle":"Ausgewähltes Asset","Assigned asset":"Zugeordnetes Asset","Actual current":"Ist-Strom","Power":"Leistung","Source state":"Quellenstatus","Status":"Status","Start charging":"Laden starten","Stop charging":"Laden stoppen","Details":"Details","Hide details":"Details schließen","Edit":"Bearbeiten","Saved":"Gespeichert","Pending":"Ausstehend","Rejected":"Abgelehnt","Next planned session":"Nächste Ladesitzung","Next action":"Nächste Aktion","No active qualified vehicle plan":"Kein aktiver Ladeplan","No qualified slots for this day.":"Keine Ladezeiten","No vehicles":"Keine Assets","No charging points":"Keine Ladepunkte","Loading":"Lädt","Error":"Fehler","No data":"Keine Daten","No connection":"Nicht verbunden","Not ready":"Nicht bereit","Waiting":"Warten","Forecast":"Prognose","If connected now":"Falls jetzt verbunden","Expected":"Erwartet","Not reserved":"Nicht reserviert","Measured power unavailable":"Keine Messdaten","Vehicle plan":"Assetplan","Charger plan":"Ladepunktplan","No forecast":"Keine Prognose","No vehicle":"Kein Asset","Tariff":"Tarif","Proposed · pale color":"Vorgeschlagen","Accepted · solid color":"Angenommen","Measured · physical source":"Gemessen","Indicative · dashed outline":"Unverbindlich","Add asset":"Asset hinzufügen","Add charger":"Ladepunkt hinzufügen","Charging mode":"Lademodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","Guest expired":"Gast abgelaufen","Ready":"Bereit","No tariff":"Kein Tarif","No solar":"Kein Solar","No deadline":"Keine Frist","No charging goal":"Kein Ladeziel","Limited power":"Begrenzte Leistung","No source":"Keine Quelle","No capacity":"Keine Kapazität","Wiring unknown":"Verdrahtung unbekannt","Guest":"Gast","Charged":"Geladen","Charging":"Lädt","Stopped":"Gestoppt","Confirmed":"Bestätigt","No action":"Keine Aktion","Reason":"Grund","Energy":"Energie","Repeat":"Wiederholen","Measured session energy":"Gemessene Sitzungsenergie","Last confirmed session":"Letzte bestätigte Sitzung","Measured energy":"Gemessene Energie","Verified cost":"Verifizierte Kosten","Current range":"Strombereich","Measured confirmation":"Messzeit","Control type":"Steuerungstyp","On/off":"Ein/Aus","Variable current":"Variabler Strom","Unverified":"Nicht verifiziert","No charger assigned":"Kein Ladepunkt zugewiesen","Target battery %":"Batterieziel %","Asset name":"Assetname","Asset type":"Assettyp","Temporary guest":"Temporärer Gast","Guest until":"Gast bis","Expected connection":"Erwartete Verbindung","Save charging site":"Ladestandort speichern","Save sources":"Quellen speichern","Maximum group kW":"Maximale Gruppenleistung kW","Group power ceiling kW":"Gruppenleistungsgrenze kW","Site name":"Standortname","Parallel chargers":"Gleichzeitige Ladepunkte","Save electrical limits":"Elektrische Grenzen speichern","Electrical limits":"Elektrische Grenzen","Battery data":"Batteriedaten","Rated power":"Nennleistung","Phases":"Phasen","Active session":"Aktive Sitzung","Add a chargeable asset":"Lade-Asset hinzufügen","Create asset":"Asset erstellen","Cancel adding":"Abbrechen","Remove":"Entfernen","blue":"Blau","orange":"Orange","green":"Grün","purple":"Lila","gold":"Gold","teal":"Blaugrün","pink":"Rosa","indigo":"Indigo","olive":"Oliv","brown":"Braun","coral":"Koralle","slate":"Schiefer","violet":"Violett","lime":"Limette","salmon":"Lachs","cyan":"Cyan","wine":"Weinrot","forest":"Waldgrün","peach":"Pfirsich","lavender":"Lavendel","turquoise":"Türkis","rust":"Rost","navy":"Marineblau","moss":"Moosgrün","Effective charging power":"Effektive Ladeleistung","Car":"Auto","Bicycle":"Fahrrad","Motorcycle":"Motorrad","Scooter":"Roller","Other":"Sonstiges","No active plan":"Kein aktiver Ladeplan","Confirm connected vehicle":"Angeschlossenes Fahrzeug bestätigen","Connected vehicle":"Angeschlossenes Fahrzeug","Not confirmed":"Nicht bestätigt"},"es":{"Overview":"Resumen","Charging Plan":"Plan de carga","Chargeable Assets":"Activos de carga","Chargers":"Puntos de carga","Settings":"Ajustes","Charging plan":"Plan de carga","Charging overview":"Resumen de carga","Refresh":"Actualizar","Today":"Hoy","Tomorrow":"Mañana","All chargers":"Todos los puntos","Show labels":"Mostrar etiquetas","Color by":"Color por","Indicative forecasting":"Previsión","Vehicle":"Activo","Charger":"Punto de carga","Vehicle + Charger":"Activo + punto","Show (not reserved)":"Mostrar","Hide":"Ocultar","Proposed":"Propuesto","Accepted":"Aceptado","Measured":"Medido","Indicative":"Indicativo","No vehicle selected":"Ningún activo seleccionado","Connected":"Conectado","Disconnected":"Desconectado","Connection unknown":"Conexión desconocida","Vehicle unknown":"Activo desconocido","Unavailable":"No disponible","Unknown":"Desconocido","Not set":"Sin definir","Not assigned":"Sin asignar","Plan color":"Color del plan","Plan labels":"Etiquetas del plan","Active chargers":"Puntos activos","Actual power":"Potencia real","Current price":"Precio actual","Charging strategy":"Modo de carga","Charging site":"Instalación de carga","Sources & bindings":"Fuentes y asignación","Safety & limits":"Seguridad y límites","Integrations":"Integraciones","Advanced & YAML":"Avanzado","Readiness":"Preparación","Battery":"Batería","Target":"Objetivo","Ready By":"Listo para","Priority":"Prioridad","Duration":"Duración","Requested energy":"Energía solicitada","Charging intention":"Necesidad de carga","Charging priority":"Prioridad de carga","Connection":"Conexión","Selected vehicle":"Activo seleccionado","Assigned asset":"Activo asignado","Actual current":"Corriente real","Power":"Potencia","Source state":"Estado de fuente","Status":"Estado","Start charging":"Iniciar carga","Stop charging":"Detener carga","Details":"Detalles","Hide details":"Cerrar detalles","Edit":"Editar","Saved":"Guardado","Pending":"Pendiente","Rejected":"Rechazado","Next planned session":"Próxima carga","Next action":"Siguiente acción","No active qualified vehicle plan":"Sin plan activo","No qualified slots for this day.":"Sin franjas de carga","No vehicles":"Sin activos","No charging points":"Sin puntos de carga","Loading":"Cargando","Error":"Error","No data":"Sin datos","No connection":"Sin conexión","Not ready":"No preparado","Waiting":"Esperando","Forecast":"Previsión","If connected now":"Si se conecta ahora","Expected":"Previsto","Not reserved":"No reservado","Measured power unavailable":"Sin datos medidos","Vehicle plan":"Plan por activo","Charger plan":"Plan por punto","No forecast":"Sin previsión","No vehicle":"Sin activo","Tariff":"Tarifa","Proposed · pale color":"Propuesto","Accepted · solid color":"Aceptado","Measured · physical source":"Medido","Indicative · dashed outline":"Indicativo","Add asset":"Añadir activo","Add charger":"Añadir punto","Charging mode":"Modo de carga","Mode":"Modo","Plan":"Plan","Home Assistant":"Home Assistant","Guest expired":"Invitado caducado","Ready":"Listo","No tariff":"Sin tarifa","No solar":"Sin energía solar","No deadline":"Sin plazo","No charging goal":"Sin objetivo","Limited power":"Potencia limitada","No source":"Sin fuente","No capacity":"Sin capacidad","Wiring unknown":"Cableado desconocido","Guest":"Invitado","Charged":"Cargado","Charging":"Cargando","Stopped":"Detenido","Confirmed":"Confirmado","No action":"Sin acción","Reason":"Motivo","Energy":"Energía","Repeat":"Repetir","Measured session energy":"Energía medida de sesión","Last confirmed session":"Última sesión confirmada","Measured energy":"Energía medida","Verified cost":"Coste verificado","Current range":"Rango de corriente","Measured confirmation":"Confirmación medida","Control type":"Tipo de control","On/off":"Encendido/apagado","Variable current":"Corriente variable","Unverified":"No verificado","No charger assigned":"Sin punto asignado","Target battery %":"Batería objetivo %","Asset name":"Nombre del activo","Asset type":"Tipo de activo","Temporary guest":"Invitado temporal","Guest until":"Invitado hasta","Expected connection":"Conexión prevista","Save charging site":"Guardar instalación","Save sources":"Guardar fuentes","Maximum group kW":"Potencia máxima del grupo kW","Group power ceiling kW":"Límite del grupo kW","Site name":"Nombre del lugar","Parallel chargers":"Puntos simultáneos","Save electrical limits":"Guardar límites","Electrical limits":"Límites eléctricos","Battery data":"Datos de batería","Rated power":"Potencia nominal","Phases":"Fases","Active session":"Sesión activa","Add a chargeable asset":"Añadir activo de carga","Create asset":"Crear activo","Cancel adding":"Cancelar","Remove":"Eliminar","blue":"Azul","orange":"Naranja","green":"Verde","purple":"Morado","gold":"Dorado","teal":"Verde azulado","pink":"Rosa","indigo":"Índigo","olive":"Oliva","brown":"Marrón","coral":"Coral","slate":"Pizarra","violet":"Violeta","lime":"Lima","salmon":"Salmón","cyan":"Cian","wine":"Granate","forest":"Verde bosque","peach":"Melocotón","lavender":"Lavanda","turquoise":"Turquesa","rust":"Óxido","navy":"Azul marino","moss":"Verde musgo","Effective charging power":"Potencia efectiva de carga","Car":"Coche","Bicycle":"Bicicleta","Motorcycle":"Motocicleta","Scooter":"Patinete","Other":"Otro","No active plan":"Sin plan activo","Confirm connected vehicle":"Confirmar vehículo conectado","Connected vehicle":"Vehículo conectado","Not confirmed":"Sin confirmar"}};
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
  PHASE_WIRING_UNVERIFIED:"Wiring unknown",NO_ASSIGNED_ASSET:"No vehicle",
  EXTERNAL_WRITER_OWNS_CHARGER:"External charging controller",
  PHYSICAL_COMMISSIONING_REQUIRED:"Verify charger safety",
  PHYSICAL_CONNECTION_UNVERIFIED:"Connection not verified",
  INDEPENDENT_POWER_UNAVAILABLE:"Power measurement missing",
  NATIVE_SWITCH_REQUIRED:"Charger control missing",
  MANUAL_START_REQUIRES_FORCE_CHARGE:"Select Force Charge",
  CONTROL_STATE_UNVERIFIED:"Control state unverified",
  PREVIOUS_COMMAND_UNCONFIRMED:"Previous command unresolved",
  PHYSICAL_PHASES_UNVERIFIED:"Wiring unknown",
  NATIVE_SWITCH_UNAVAILABLE:"Charger unavailable",
  MANUAL_ONE_OFF_NOT_AVAILABLE:"Unavailable"

};
function mcReason(value){return mcTr(MC_REASONS[value]||"Unavailable");}
const MC_TABS = ["Overview", "Charging Plan", "Chargeable Assets", "Chargers", "Settings"];
const MC_SETTINGS = ["Charging site", "Sources & bindings", "Charging strategy", "Safety & limits", "Integrations", "Advanced & YAML"];
// Pause is a persistent Charger admission hold, not a second strategy.
for (const [locale, terms] of Object.entries({
  nl:{"Pause charging":"Laden pauzeren","Resume charging":"Laden hervatten","Paused":"Gepauzeerd","Ready for next plan":"Klaar voor volgend laadplan"},
  fr:{"Pause charging":"Mettre en pause","Resume charging":"Reprendre","Paused":"En pause","Ready for next plan":"Prêt pour le prochain plan"},
  da:{"Pause charging":"Sæt opladning på pause","Resume charging":"Genoptag opladning","Paused":"Sat på pause","Ready for next plan":"Klar til næste plan"},
  nb:{"Pause charging":"Sett lading på pause","Resume charging":"Gjenoppta lading","Paused":"Pauset","Ready for next plan":"Klar for neste plan"},
  sv:{"Pause charging":"Pausa laddning","Resume charging":"Återuppta laddning","Paused":"Pausad","Ready for next plan":"Klar för nästa plan"},
  de:{"Pause charging":"Laden pausieren","Resume charging":"Laden fortsetzen","Paused":"Pausiert","Ready for next plan":"Bereit für den nächsten Plan"},
  es:{"Pause charging":"Pausar carga","Resume charging":"Reanudar carga","Paused":"En pausa","Ready for next plan":"Listo para el próximo plan"}
}))Object.assign(MC_TEXT[locale],terms);
for(const [locale,translations] of Object.entries({
  nl:{"Configure in Home Assistant":"Configureren in Home Assistant","Selected":"Geselecteerd"},
  fr:{"Configure in Home Assistant":"Configurer dans Home Assistant","Selected":"Sélectionné"},
  da:{"Configure in Home Assistant":"Konfigurer i Home Assistant","Selected":"Valgt"},
  nb:{"Configure in Home Assistant":"Konfigurer i Home Assistant","Selected":"Valgt"},
  sv:{"Configure in Home Assistant":"Konfigurera i Home Assistant","Selected":"Vald"},
  de:{"Configure in Home Assistant":"In Home Assistant konfigurieren","Selected":"Ausgewählt"},
  es:{"Configure in Home Assistant":"Configurar en Home Assistant","Selected":"Seleccionado"}
}))Object.assign(MC_TEXT[locale],translations);
// One Asset-side chooser; all writes still target the Charger-owned Config Entry.
for(const [locale,terms] of Object.entries({
  nl:{"Assign charger":"Laadpaal toewijzen","Change charger":"Laadpaal wijzigen","Select charger":"Kies laadpaal","Assign selected charger":"Laadpaal toewijzen","Unassign charger":"Laadpaal loskoppelen","No free charger":"Geen vrije laadpaal","Close assignment":"Sluiten","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Alleen bij stilstand. Stop het laden apart vóór de overdracht."},
  fr:{"Assign charger":"Attribuer une borne","Change charger":"Changer de borne","Select charger":"Choisir une borne","Assign selected charger":"Attribuer cette borne","Unassign charger":"Désattribuer la borne","No free charger":"Aucune borne libre","Close assignment":"Fermer","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Uniquement à l'arrêt. Arrêtez la recharge avant de déplacer un véhicule."},
  da:{"Assign charger":"Tildel lader","Change charger":"Skift lader","Select charger":"Vælg lader","Assign selected charger":"Tildel valgt lader","Unassign charger":"Fjern tilknytning","No free charger":"Ingen ledig lader","Close assignment":"Luk","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Kun ved stilstand. Stop opladning før flytning af køretøjet."},
  nb:{"Assign charger":"Tildel lader","Change charger":"Bytt lader","Select charger":"Velg lader","Assign selected charger":"Tildel valgt lader","Unassign charger":"Fjern tilordning","No free charger":"Ingen ledig lader","Close assignment":"Lukk","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Bare når laderne er stoppet. Stopp lading før flytting."},
  sv:{"Assign charger":"Tilldela laddare","Change charger":"Byt laddare","Select charger":"Välj laddare","Assign selected charger":"Tilldela vald laddare","Unassign charger":"Ta bort tilldelning","No free charger":"Ingen ledig laddare","Close assignment":"Stäng","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Endast i viloläge. Stoppa laddning före flytt."},
  de:{"Assign charger":"Ladepunkt zuweisen","Change charger":"Ladepunkt wechseln","Select charger":"Ladepunkt auswählen","Assign selected charger":"Ladepunkt zuweisen","Unassign charger":"Zuweisung aufheben","No free charger":"Kein freier Ladepunkt","Close assignment":"Schließen","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Nur im Stillstand. Laden vor dem Wechsel separat stoppen."},
  es:{"Assign charger":"Asignar cargador","Change charger":"Cambiar cargador","Select charger":"Elegir cargador","Assign selected charger":"Asignar cargador elegido","Unassign charger":"Quitar asignación","No free charger":"No hay cargadores libres","Close assignment":"Cerrar","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Solo en reposo. Detenga la carga antes de cambiar el vehículo."}
}))Object.assign(MC_TEXT[locale],terms);
for(const [locale,terms] of Object.entries({
  nl:{"Stop charging before changing charger":"Stop eerst met laden voordat je van laadpaal wisselt","Settings changed; refresh and retry":"Instellingen gewijzigd; vernieuw en probeer opnieuw"},
  fr:{"Stop charging before changing charger":"Arrêtez la charge avant de changer de borne","Settings changed; refresh and retry":"Paramètres modifiés ; actualisez et réessayez"},
  da:{"Stop charging before changing charger":"Stop opladning før skift af lader","Settings changed; refresh and retry":"Indstillinger ændret; opdater og prøv igen"},
  nb:{"Stop charging before changing charger":"Stopp lading før bytte av lader","Settings changed; refresh and retry":"Innstillinger endret; oppdater og prøv igjen"},
  sv:{"Stop charging before changing charger":"Stoppa laddning innan du byter laddare","Settings changed; refresh and retry":"Inställningarna har ändrats; uppdatera och försök igen"},
  de:{"Stop charging before changing charger":"Laden vor dem Ladepunktwechsel stoppen","Settings changed; refresh and retry":"Einstellungen geändert; aktualisieren und erneut versuchen"},
  es:{"Stop charging before changing charger":"Detenga la carga antes de cambiar de cargador","Settings changed; refresh and retry":"La configuración cambió; actualice e inténtelo de nuevo"}
}))Object.assign(MC_TEXT[locale],terms);
for(const [locale,translation] of Object.entries({"nl":"Wijs eerst het andere voertuig af","fr":"Désattribuez d'abord l'autre véhicule","da":"Fjern først det andet køretøjs tilknytning","nb":"Fjern tilordningen for det andre kjøretøyet først","sv":"Ta först bort det andra fordonets tilldelning","de":"Zuerst die Zuweisung des anderen Fahrzeugs aufheben","es":"Quite primero la asignación del otro vehículo"}))
  MC_TEXT[locale]["Unassign the other vehicle first"]=translation;
const keysForMinimalCharger=["Start unavailable","External charging controller","Verify charger safety","Connection not verified","Power measurement missing","Charger control missing","Select Force Charge","Control state unverified","Previous command unresolved","Charger unavailable"];
for(const [locale,labels] of Object.entries({"nl":["Start niet beschikbaar","Externe laadsturing actief","Controleer eerst de veiligheid van de laadpaal","Aansluiting niet bevestigd","Vermogensmeting ontbreekt","Laadsturing ontbreekt","Selecteer Force Charge","Controlestatus onbekend","Vorige opdracht onbeslist","Laadpaal niet beschikbaar"],"fr":["Démarrage indisponible","Contrôleur de charge externe","Vérifier la sécurité de la borne","Connexion non vérifiée","Mesure de puissance absente","Commande de borne absente","Choisir Force Charge","État de commande non vérifié","Commande précédente non résolue","Borne indisponible"],"da":["Start ikke tilgængelig","Ekstern ladestyring","Kontroller laderens sikkerhed","Forbindelse ikke bekræftet","Effektmåling mangler","Ladestyring mangler","Vælg Force Charge","Styringstilstand ukendt","Tidligere kommando uafklaret","Lader utilgængelig"],"nb":["Start ikke tilgjengelig","Ekstern ladekontroll","Bekreft laderens sikkerhet","Tilkobling ikke bekreftet","Effektmåling mangler","Ladekontroll mangler","Velg Force Charge","Kontrollstatus ubekreftet","Forrige kommando uavklart","Lader utilgjengelig"],"sv":["Start ej tillgänglig","Extern laddstyrning","Verifiera laddarens säkerhet","Anslutning ej bekräftad","Effektmätning saknas","Laddstyrning saknas","Välj Force Charge","Styrstatus ej verifierad","Föregående kommando olöst","Laddare otillgänglig"],"de":["Start nicht verfügbar","Externe Ladesteuerung","Sicherheit des Ladepunkts prüfen","Verbindung nicht bestätigt","Leistungsmessung fehlt","Ladesteuerung fehlt","Force Charge auswählen","Steuerstatus ungeprüft","Vorheriger Befehl ungeklärt","Ladepunkt nicht verfügbar"],"es":["Inicio no disponible","Control de carga externo","Verifique la seguridad del cargador","Conexión no verificada","Falta medición de potencia","Falta control del cargador","Seleccione Force Charge","Estado de control no verificado","Comando anterior sin resolver","Cargador no disponible"]}))
  keysForMinimalCharger.forEach((key,i)=>{MC_TEXT[locale][key]=labels[i];});
for(const [locale,terms] of Object.entries({"nl":["Indicatieve variabele energiekosten","Schatting op basis van gemeten vermogen, geen factuur"],"fr":["Coût énergétique variable indicatif","Estimation fondée sur la puissance mesurée, pas une facture"],"de":["Geschätzte variable Energiekosten","Aus Messleistung berechnete Schätzung, keine Rechnung"],"es":["Coste variable de energía estimado","Estimación de potencia medida, no es una factura"],"da":["Anslået variabel energiomkostning","Estimat fra målt effekt, ikke en faktura"],"nb":["Anslått variabel energikostnad","Estimat fra målt effekt, ikke en faktura"],"sv":["Beräknad rörlig energikostnad","Uppskattning från uppmätt effekt, inte en faktura"]})){
  MC_TEXT[locale]["Indicative variable energy cost"]=terms[0];
  MC_TEXT[locale]["Power-derived estimate, not a bill"]=terms[1];
}
for(const [locale,labels] of Object.entries({"nl":["Variabel referentietarief","Spotprijs"],"fr":["Prix de référence variable","Prix spot"],"de":["Variabler Referenzpreis","Spotpreis"],"es":["Precio variable de referencia","Precio spot"],"da":["Variabel referencepris","Spotpris"],"nb":["Variabel referansepris","Spotpris"],"sv":["Rörligt referenspris","Spotpris"]})){
  MC_TEXT[locale]["Variable reference price"]=labels[0];
  MC_TEXT[locale]["Spot price"]=labels[1];
}
for(const [locale,b] of Object.entries({
  nl:["Conservatieve bovengrens budget","Budget resterend (conservatief)","Budgetvoortgang"],
  fr:["Plafond prudent du budget","Budget restant (prudent)","Suivi du budget"],
  da:["Konservativ budgetgrænse","Resterende budget (konservativt)","Budgetforbrug"],
  nb:["Konservativ budsjettgrense","Resterende budsjett (konservativt)","Budsjettfremdrift"],
  sv:["Konservativ budgetgräns","Återstående budget (konservativt)","Budgetförbrukning"],
  de:["Konservative Budgetobergrenze","Restbudget (konservativ)","Budgetfortschritt"],
  es:["Límite superior conservador","Presupuesto restante (prudente)","Progreso del presupuesto"]
})){
  for(const [i,key] of ["Conservative budget upper bound",
     "Budget remaining (conservative)","Budget progress"].entries())
    MC_TEXT[locale][key]=b[i];
}
for(const [locale,b] of Object.entries({
  nl:["Laadpatroon","Flexibele goedkoopste kwartieren","Eén aaneengesloten laadsessie",
      "Aaneengesloten laden en prijsstrategie"],
  fr:["Mode de recharge","Créneaux les moins chers","Une recharge continue",
      "Continuité et stratégie tarifaire"],
  da:["Lademønster","Billigste fleksible kvarter","Én sammenhængende opladning",
      "Kontinuitet og prisstrategi"],
  nb:["Lademønster","Billigste fleksible kvarter","Én sammenhengende lading",
      "Kontinuitet og prisstrategi"],
  sv:["Laddmönster","Billigaste flexibla kvartarna","En sammanhängande laddning",
      "Kontinuitet och prisstrategi"],
  de:["Lademuster","Flexible günstigste Viertelstunden","Ein durchgehender Ladevorgang",
      "Kontinuität und Preisstrategie"],
  es:["Patrón de carga","Intervalos flexibles más baratos","Una carga continua",
      "Continuidad y estrategia de precio"]
})){
  for(const [i,key] of ["Charging pattern","Flexible cheapest quarters",
    "One continuous charge","Continuity and price strategy"].entries())
    MC_TEXT[locale][key]=b[i];
}
for(const [locale,b] of Object.entries({
  nl:["Minimum laden vóór prijsgrens","Prijsplafond per kWh",
      "Onmiddellijk laden bij lage prijs","Onmiddellijk laden bij lage SoC",
      "Opportunistisch percentage","Prijsvaluta","Kies eerst de valuta",
      "Stel valuta in","Vroegste start instellen","Opportunistisch laden",
      "Type 1 — fractie van prijsplafond","Type 2 — prijs volgende dag"],
  fr:["Minimum avant le plafond","Plafond de prix par kWh",
      "Seuil de prix bas immédiat","Seuil batterie faible immédiat",
      "Pourcentage opportuniste","Devise tarifaire","Choisir d'abord la devise",
      "Choisir la devise","Définir le début le plus tôt","Charge opportuniste",
      "Type 1 — fraction du plafond","Type 2 — prix de demain"],
  de:["Mindestladung vor Preislimit","Preislimit pro kWh",
      "Sofortladen bei Niedrigpreis","Sofortladen bei niedrigem Akkustand",
      "Opportunistischer Prozentsatz","Preiswährung","Zuerst Währung wählen",
      "Währung einstellen","Frühester Start","Opportunistisches Laden",
      "Typ 1 — Preislimitanteil","Typ 2 — morgiger Preis"]
})){
  for(const [i,key] of ["Minimum charge before price limits","Price ceiling per kWh",
    "Immediate low-price threshold","Immediate low-SoC threshold",
    "Opportunistic percentage","Price currency",
    "Choose currency before price limits","Set price currency",
    "Set earliest start","Opportunistic charging",
    "Type 1 — cap fraction","Type 2 — tomorrow price"].entries())
    MC_TEXT[locale][key]=b[i];
}
const MC_NOVICE_UX_WORDS=["All charging · Power & price","Shaded planned · outlined accepted · solid measured · price line","Power","Price unavailable","reference price, not an invoice","Price intervals incomplete; missing periods are not zero","Still planned","charger","chargers","Charging per vehicle and charger","No qualified physical or planned power in this period","Set charging goal","I want to charge to","Battery target (%)","Extra energy (kWh)","Charging time (minutes)","Charging budget (€)","Amount","Save charging goal","Indicative energy budget, not a guaranteed electricity bill","Schedule charging","Hide charging schedule","When should the vehicle be ready?","Set one-time or daily Ready By","Add guest or vehicle","Charging pattern","Price ceiling per kWh","Next charge","Shortfall","Measured power is attributed to this charger; vehicle may be unknown","No qualified timeline"];
for(const [locale,translations] of Object.entries({"nl":["Totaal laden · Vermogen en prijs","Transparant gepland · omlijnd bevestigd · gevuld gemeten · prijslijn","Vermogen","Prijs niet beschikbaar","referentieprijs, geen factuur","Prijsperioden onvolledig; ontbrekende waarden zijn niet nul","Nog gepland","laadpaal","laadpalen","Laden per voertuig en laadpaal","Geen bevestigd gemeten of gepland vermogen in deze periode","Laaddoel instellen","Ik wil laden tot","Batterijdoel (%)","Extra energie (kWh)","Laadduur (minuten)","Laadbudget (€)","Hoeveelheid","Laaddoel opslaan","Indicatief energiebudget, geen gegarandeerde stroomfactuur","Laadtijden instellen","Laadtijden verbergen","Wanneer moet het voertuig klaar zijn?","Eenmalig of dagelijks gereed instellen","Gast of voertuig toevoegen","Laadpatroon","Maximumprijs per kWh","Volgende laadbeurt","Tekort","Gemeten vermogen hoort bij deze laadpaal; voertuig kan onbekend zijn","Geen bevestigde tijdlijn"],"fr":["Recharge totale · Puissance et prix","Prévu en transparence · accepté en contour · mesuré en plein · courbe de prix","Puissance","Prix indisponible","prix indicatif, pas une facture","Créneaux de prix incomplets ; absence ne signifie pas zéro","Encore prévu","borne","bornes","Recharge par véhicule et borne","Aucune puissance mesurée ou planifiée vérifiée pour cette période","Définir l'objectif de charge","Je veux charger jusqu'à","Batterie cible (%)","Énergie supplémentaire (kWh)","Durée de charge (minutes)","Budget de charge (€)","Quantité","Enregistrer l'objectif","Budget énergétique indicatif, pas une facture garantie","Programmer la charge","Masquer le calendrier","Quand le véhicule doit-il être prêt ?","Définir une échéance unique ou quotidienne","Ajouter un invité ou véhicule","Mode de charge","Prix maximal par kWh","Prochaine charge","Manque","Puissance mesurée attribuée à la borne ; véhicule éventuellement inconnu","Aucune chronologie qualifiée"],"de":["Gesamtladen · Leistung und Preis","Schattiert geplant · umrandet bestätigt · voll gemessen · Preislinie","Leistung","Preis nicht verfügbar","Referenzpreis, keine Rechnung","Preisintervalle unvollständig; fehlende Werte sind nicht null","Noch geplant","Ladepunkt","Ladepunkte","Laden nach Fahrzeug und Ladepunkt","Keine bestätigte Ladeleistung oder Planung in diesem Zeitraum","Ladeziel festlegen","Ich möchte laden bis","Batterieziel (%)","Zusätzliche Energie (kWh)","Ladedauer (Minuten)","Ladebudget (€)","Menge","Ladeziel speichern","Unverbindliches Energiebudget, keine garantierte Stromrechnung","Ladezeiten planen","Ladezeiten ausblenden","Wann soll das Fahrzeug bereit sein?","Einmalige oder tägliche Zielzeit","Gast oder Fahrzeug hinzufügen","Lademuster","Höchstpreis pro kWh","Nächste Ladung","Fehlmenge","Messleistung gehört zum Ladepunkt; Fahrzeug kann unbekannt sein","Keine qualifizierte Zeitachse"],"es":["Carga total · Potencia y precio","Sombreado planificado · contorno aceptado · sólido medido · línea de precio","Potencia","Precio no disponible","precio de referencia, no una factura","Intervalos de precio incompletos; lo desconocido no es cero","Aún previsto","cargador","cargadores","Carga por vehículo y cargador","No hay potencia medida ni planificada verificada en este período","Definir objetivo de carga","Quiero cargar hasta","Objetivo batería (%)","Energía extra (kWh)","Tiempo de carga (minutos)","Presupuesto de carga (€)","Cantidad","Guardar objetivo de carga","Presupuesto energético orientativo, no una factura garantizada","Programar carga","Ocultar horarios","¿Cuándo debe estar listo el vehículo?","Definir hora única o diaria","Añadir invitado o vehículo","Patrón de carga","Precio máximo por kWh","Siguiente carga","Déficit","La potencia medida corresponde al cargador; el vehículo puede ser desconocido","No hay cronología verificada"],"da":["Samlet opladning · Effekt og pris","Skygget planlagt · omridset godkendt · udfyldt målt · prislinje","Effekt","Pris utilgængelig","referencepris, ikke en faktura","Prisintervaller ufuldstændige; ukendt er ikke nul","Stadig planlagt","lader","ladere","Opladning pr. køretøj og lader","Ingen verificeret målt eller planlagt effekt i perioden","Indstil lademål","Jeg vil lade op til","Batterimål (%)","Ekstra energi (kWh)","Ladetid (minutter)","Ladebudget (€)","Mængde","Gem lademål","Vejledende energibudget, ikke en garanteret elregning","Planlæg opladning","Skjul ladeplan","Hvornår skal bilen være klar?","Indstil engangs- eller dagligt klar-tidspunkt","Tilføj gæst eller køretøj","Lademønster","Maksimumpris pr. kWh","Næste opladning","Mangel","Målt effekt tilhører laderen; køretøjet kan være ukendt","Ingen kvalificeret tidslinje"],"nb":["Samlet lading · Effekt og pris","Skygget planlagt · omrisset godkjent · fylt målt · prislinje","Effekt","Pris utilgjengelig","referansepris, ikke en faktura","Prisintervaller ufullstendige; ukjent er ikke null","Fortsatt planlagt","lader","ladere","Lading per kjøretøy og lader","Ingen verifisert målt eller planlagt effekt i perioden","Sett lademål","Jeg vil lade til","Batterimål (%)","Ekstra energi (kWh)","Ladetid (minutter)","Ladebudsjett (€)","Mengde","Lagre lademål","Veiledende energibudsjett, ikke garantert strømregning","Planlegg lading","Skjul ladeplan","Når må bilen være klar?","Sett engangs- eller daglig klartid","Legg til gjest eller kjøretøy","Lademønster","Makspris per kWh","Neste lading","Underskudd","Målt effekt gjelder laderen; kjøretøy kan være ukjent","Ingen kvalifisert tidslinje"],"sv":["Total laddning · Effekt och pris","Skuggat planerat · kontur accepterat · fyllt uppmätt · prislinje","Effekt","Pris saknas","referenspris, inte en faktura","Prisintervall ofullständiga; saknat värde är inte noll","Återstår planerat","laddare","laddare","Laddning per fordon och laddare","Ingen verifierad uppmätt eller planerad effekt under perioden","Ange laddmål","Jag vill ladda till","Batterimål (%)","Extra energi (kWh)","Laddtid (minuter)","Laddbudget (€)","Belopp","Spara laddmål","Ungefärlig energibudget, ingen garanterad elräkning","Schemalägg laddning","Dölj laddschema","När ska fordonet vara klart?","Ställ in engångs- eller daglig klartid","Lägg till gäst eller fordon","Laddmönster","Maxpris per kWh","Nästa laddning","Underskott","Uppmätt effekt tillhör laddaren; fordonet kan vara okänt","Ingen kvalificerad tidslinje"]})){
  MC_NOVICE_UX_WORDS.forEach((key,index)=>{MC_TEXT[locale][key]=translations[index];});
}
const MC_DAY_NAMES={
  mon:"Monday",tue:"Tuesday",wed:"Wednesday",thu:"Thursday",
  fri:"Friday",sat:"Saturday",sun:"Sunday"
};
const MC_CLOCKS=Array.from({length:96},(_,index)=>
  String(Math.floor(index/4)).padStart(2,"0")+":"+
  String((index%4)*15).padStart(2,"0"));
for(const [locale,terms] of Object.entries({
  nl:{"Once":"Eenmalig","Daily":"Dagelijks","Specific days":"Specifieke dagen",
    "Monday":"Maandag","Tuesday":"Dinsdag","Wednesday":"Woensdag",
    "Thursday":"Donderdag","Friday":"Vrijdag","Saturday":"Zaterdag","Sunday":"Zondag",
    "Allowed charging times":"Toegestane laaduren","Charging days":"Laaddagen",
    "No day selected":"Dag niet geselecteerd","Window enabled":"Venster actief",
    "Window disabled":"Geen venster","Start hour":"Startuur","End hour":"Einduur",
    "Select at least one weekday":"Selecteer minstens één weekdag"},
  fr:{"Once":"Une fois","Daily":"Chaque jour","Specific days":"Jours spécifiques",
    "Monday":"Lundi","Tuesday":"Mardi","Wednesday":"Mercredi","Thursday":"Jeudi",
    "Friday":"Vendredi","Saturday":"Samedi","Sunday":"Dimanche",
    "Allowed charging times":"Heures de recharge autorisées","Charging days":"Jours de recharge",
    "No day selected":"Jour non sélectionné","Window enabled":"Plage active",
    "Window disabled":"Aucune plage","Start hour":"Début","End hour":"Fin",
    "Select at least one weekday":"Sélectionnez au moins un jour"},
  de:{"Once":"Einmalig","Daily":"Täglich","Specific days":"Bestimmte Tage",
    "Allowed charging times":"Erlaubte Ladezeiten"},
  es:{"Once":"Una vez","Daily":"Diario","Specific days":"Días específicos",
    "Allowed charging times":"Horarios de carga permitidos"},
  da:{"Once":"Én gang","Daily":"Dagligt","Specific days":"Bestemte dage",
    "Allowed charging times":"Tilladte ladetider"},
  nb:{"Once":"Én gang","Daily":"Daglig","Specific days":"Bestemte dager",
    "Allowed charging times":"Tillatte ladetider"},
  sv:{"Once":"En gång","Daily":"Dagligen","Specific days":"Specifika dagar",
    "Allowed charging times":"Tillåtna laddtider"}
}))Object.assign(MC_TEXT[locale],terms);
const MC_MODES = ["Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"];
const MC_STYLE = [
  ":host{display:block;color:var(--primary-text-color,#20252b);font:inherit}",
  ".root{background:var(--ha-card-background,var(--card-background-color,#fff));border:1px solid var(--divider-color,#e5e7eb);border-radius:14px;padding:20px;box-shadow:0 1px 4px #0000000b}",
  ".heading{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}",
  "h2{font-size:20px;font-weight:650;line-height:1.4;margin:0 0 8px}h3{font-size:15px;font-weight:600;margin:0}p{margin:5px 0;line-height:1.5}",
  ".muted{color:var(--secondary-text-color,#65717e)}.small{font-size:12px}.value{font-weight:700;font-size:22px}",
  ".tabs,.controls,.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.tabs{gap:3px;border-bottom:1px solid var(--divider-color,#e5e7eb);margin-bottom:20px}",
  "input,button,select,textarea,a.action{font:inherit;border:1px solid var(--divider-color,#cfd6de);background:var(--card-background-color,#fff);color:inherit;border-radius:8px;padding:9px 11px;cursor:pointer;text-decoration:none;min-height:40px}.tabs button{border:0;border-bottom:3px solid transparent;border-radius:0;background:transparent;padding:10px 13px;color:var(--secondary-text-color,#667085)}",
  ".tabs button[aria-selected=true]{color:var(--primary-color,#1976d2);border-bottom-color:var(--primary-color,#1976d2);background:transparent;font-weight:650}button.active{background:var(--primary-color,#1976d2);color:var(--text-primary-color,#fff);border-color:var(--primary-color,#1976d2)}",
  "button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid var(--primary-color,#1976d2);outline-offset:2px}",
  ".grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}",
  ".card{border:1px solid var(--divider-color,#e1e4e8);border-radius:10px;padding:14px;min-width:0;margin:8px 0}.settings-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:12px;margin-top:14px}.settings-card{margin:0;min-height:72px}.settings-card.expanded{grid-column:1/-1}.settings-heading{min-width:0;flex:1}.settings-heading p{margin-top:5px}.settings-card .row{align-items:flex-start}.config-code{white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;border:1px solid var(--divider-color,#e1e4e8);border-radius:8px;background:var(--secondary-background-color,#f7f8fa);font-size:12px;line-height:1.5}",
  ".metric{background:var(--secondary-background-color,#f6f8fa);border:1px solid var(--divider-color,#e1e4e8);border-radius:10px;padding:15px;min-width:0}",
  ".row{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}",
  ".details{margin-top:10px;padding-top:9px;border-top:1px solid var(--divider-color,#ddd)}.assignment-editor{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.assignment-editor p{flex-basis:100%}.assignment-editor select{width:100%;min-width:0;max-width:100%;box-sizing:border-box}",
  ".pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:5px 0}",
  ".field{display:flex;flex-direction:column;gap:4px;margin:8px 0}.field label{font-size:13px;color:var(--secondary-text-color,#65717e)}",
  ".field input,.field select{width:100%;box-sizing:border-box;padding:10px;border:1px solid var(--divider-color,#cfd6de);background:var(--card-background-color,#fff);color:inherit;border-radius:8px}.yaml-editor{margin:12px 0;padding:18px;border:1px solid var(--divider-color,#ccd4de);border-radius:10px;max-width:100%;box-sizing:border-box}.yaml-editor textarea{display:block;width:100%;box-sizing:border-box;min-height:340px;resize:vertical;font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;background:var(--secondary-background-color,#f7f8fa);margin-top:8px}.yaml-editor select{width:100%;max-width:100%;box-sizing:border-box}.yaml-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.yaml-editor pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}.yaml-error{border-left:3px solid var(--error-color,#bb3939);padding:8px 12px}.settings-toolbar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0;align-items:center}",
  ".message{font-size:13px;margin:9px 0}.pending{color:var(--warning-color,#b57418)}.confirmed{color:var(--success-color,#278355)}",
  ".notice{border:1px solid var(--divider-color,#e5e7eb);border-radius:8px;padding:11px 13px;background:var(--secondary-background-color,#f6f8fa);margin:12px 0;font-size:13px}",
  ".error{border-color:var(--error-color,#d43b38)}.chart{overflow-x:auto;width:100%}",
  ".legend{display:flex;flex-wrap:wrap;gap:15px;font-size:12px;color:var(--secondary-text-color,#65717e)}",
  ".dot{display:inline-block;width:11px;height:11px;margin-right:5px;border-radius:2px}",
  ".plan-lane{margin:10px 0;border:1px solid var(--divider-color,#d8dde3);border-radius:11px;padding:11px}",
  ".plan-lane svg{display:block;min-width:680px;width:100%;height:auto}",
  ".plan-lane .chart{margin-top:5px}",
  ".combined-plan{margin:12px 0 18px}.combined-plan svg{display:block;width:100%;height:auto;min-width:0}.combined-plan .chart{overflow:hidden}.lane-summary{overflow-wrap:anywhere}.quick-goal{margin:10px 0;padding:10px;border:1px solid var(--divider-color,#ddd);border-radius:9px;background:var(--secondary-background-color,#f6f8fa)}.quick-goal h4{font-size:14px;margin:0 0 6px}.goal-controls{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(90px,1fr);gap:10px}.quick-goal button{margin-top:6px}.schedule-editor{margin:8px 0}.overview-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}",
  "@media(max-width:600px){.goal-controls{grid-template-columns:1fr}.quick-goal{padding:9px}.combined-plan svg text{font-size:10px}.plan-lane{padding:8px}}",
  ".plan-key{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:6px 0;font-size:12px}",
  ".plan-swatch{width:12px;height:12px;border-radius:3px;display:inline-block;margin-right:4px}",
  ".plan-caution{font-size:12px;color:var(--secondary-text-color,#65717e);line-height:1.5}",
  "svg{width:100%;min-width:440px;height:220px}svg text{fill:var(--secondary-text-color,#65717e);font-size:11px}",
  "@media(max-width:600px){.root{padding:12px}.grid{grid-template-columns:1fr}.tabs{display:flex;overflow-x:auto;flex-wrap:nowrap}.tabs button{font-size:12px;padding:9px 10px;white-space:nowrap;flex-shrink:0}.settings-grid{grid-template-columns:1fr}}"
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

// One Basic-style power/price overview above the existing per-Charger lanes.
// Never invent unavailable meter samples, convert a quote to a bill, or
// attribute anonymous historical power to today's selected vehicle.
function mcCombinedChargingChart(data, visibleChargers, slots, actuals){
  const wrapper=mcEl("section","card combined-plan");
  wrapper.append(mcEl("h3","",mcTr("All charging · Power & price")));
  wrapper.append(mcEl("p","muted small",
    mcTr("Shaded planned · outlined accepted · solid measured · price line")));
  const from=Date.parse(data.start), until=Date.parse(data.end);
  if(!Number.isFinite(from)||!Number.isFinite(until)||until<=from){
    wrapper.append(mcEl("p","muted",mcTr("No qualified timeline")));
    return wrapper;
  }
  const count=Math.ceil((until-from)/900000);
  if(count>200){
    wrapper.append(mcEl("p","muted",mcTr("Unavailable")));
    return wrapper;
  }
  const visible=new Set(visibleChargers.map(x=>x.id));
  const buckets=Array.from({length:count},()=>({
    proposed:null,accepted:null,actual:null,price:null
  }));
  function collect(rows,key){
    for(const row of rows){
      if(!visible.has(row.charger_id)||typeof row[key]!=="number"||
         !Number.isFinite(row[key])||row[key]<0)continue;
      const start=Date.parse(row.start),end=Date.parse(row.end);
      if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)continue;
      const ix=Math.round((start-from)/900000);
      if(ix<0||ix>=count||Math.abs(start-(from+ix*900000))>50)continue;
      // Data contract has one sourced 15-minute row per Charger per field.
      if(end-start!==900000)continue;
      const k=key==="actual_power_kw"?"actual":
        key==="accepted_power_kw"?"accepted":"proposed";
      buckets[ix][k]=(buckets[ix][k]??0)+row[key];
    }
  }
  collect(slots,"proposed_power_kw");
  collect(slots,"accepted_power_kw");
  collect(actuals,"actual_power_kw");
  const quotes=Array.isArray(data.price_slots)?data.price_slots.filter(q=>
    typeof q.price_per_kwh==="number"&&Number.isFinite(q.price_per_kwh)&&
    typeof q.currency==="string"&&q.currency.length===3):[];
  const currencies=[...new Set(quotes.map(x=>x.currency))];
  const basis=[...new Set(quotes.map(x=>x.basis||"unqualified"))];
  let priceReady=currencies.length===1&&basis.length===1;
  if(priceReady){
    for(let i=0;i<count;i++){
      const start=from+i*900000;
      const matched=quotes.filter(q=>Date.parse(q.start)<=start&&
        Date.parse(q.end)>=start+900000);
      if(matched.length===1)buckets[i].price=matched[0].price_per_kwh;
    }
  }
  const values=buckets.flatMap(x=>
    [x.proposed,x.accepted,x.actual].filter(Number.isFinite));
  const cap=Math.max(0.5,...values,0);
  const priceValues=priceReady?buckets.map(x=>x.price).filter(Number.isFinite):[];
  const lo=priceValues.length?Math.min(...priceValues):0;
  const hi=priceValues.length?Math.max(...priceValues):0;
  const spread=hi-lo||1;
  const x0=69,width=807,top=34,bottom=190,height=bottom-top;
  const svg=mcSVG("svg",{
    viewBox:"0 0 960 246",role:"img",class:"timeline",
    "aria-label":mcTr("Combined actual charging power, planned and accepted charging, and independently scaled electricity price")
  });
  svg.append(mcSVG("text",{x:4,y:16,"font-size":13},mcTr("Power")+" · kW"));
  svg.append(mcSVG("text",{x:955,y:16,"text-anchor":"end","font-size":12},
    priceValues.length?basis[0]+" · "+currencies[0]+"/kWh":
      mcTr("Price unavailable")));
  svg.append(mcSVG("line",{x1:x0,y1:bottom,x2:x0+width,y2:bottom,
    stroke:"currentColor","stroke-opacity":0.35}));
  for(let t=0;t<=4;t++){
    const y=bottom-t*height/4;
    svg.append(mcSVG("line",{x1:x0,y1:y,x2:x0+width,y2:y,
      stroke:"currentColor","stroke-opacity":0.12}));
    svg.append(mcSVG("text",{x:x0-7,y:y+4,"text-anchor":"end",
      "font-size":11},(t*cap/4).toFixed(1)));
  }
  const colors={proposed:"#667e9f",accepted:"#326f9d",actual:"#18856d"};
  const layers=[["proposed",0.18],["accepted",0.8],["actual",1]];
  for(let i=0;i<count;i++){
    const tick=buckets[i];
    const x=x0+i*width/count,bar=width/count;
    for(const [key,opacity] of layers){
      const kw=tick[key];
      if(!Number.isFinite(kw))continue;
      const bh=Math.min(height,(kw/cap)*height);
      const rect=mcSVG("rect",{
        x:x+(key==="proposed"?0:key==="accepted"?bar*0.10:bar*0.20),
        y:bottom-bh,width:Math.max(0.6,bar*(key==="proposed"?0.88:0.68)),
        height:bh,fill:key==="accepted"?"none":colors[key],
        "fill-opacity":opacity,stroke:key==="accepted"?colors[key]:"none",
        "stroke-width":key==="accepted"?1:0
      });
      rect.append(mcSVG("title",{},
        mcTr(key==="actual"?"Measured":key==="accepted"?"Accepted":"Proposed")+
        " · "+mcTime(new Date(from+i*900000).toISOString(),data.timezone)+
        " · "+kw.toFixed(2)+" kW"));
      svg.append(rect);
    }
  }
  if(priceValues.length){
    let d="",last=-2;
    for(let i=0;i<count;i++){
      const price=buckets[i].price;
      if(!Number.isFinite(price)){last=-2;continue;}
      const x=x0+(i+0.5)*width/count;
      const y=bottom-(price-lo)/spread*height;
      d+=(i===last+1?" L":" M")+x.toFixed(2)+" "+y.toFixed(2);
      last=i;
    }
    if(d)svg.append(mcSVG("path",{d,fill:"none",stroke:"#ab6d13",
      "stroke-width":2,"stroke-linecap":"round","stroke-linejoin":"round"}));
    for(let i=0;i<count;i++){
      const price=buckets[i].price;
      if(!Number.isFinite(price))continue;
      const circle=mcSVG("circle",{
        cx:x0+(i+0.5)*width/count,
        cy:bottom-(price-lo)/spread*height,
        r:Math.max(1.5,Math.min(2.5,width/count/2)),
        fill:"#ab6d13"
      });
      circle.append(mcSVG("title",{},
        mcTime(new Date(from+i*900000).toISOString(),data.timezone)+
        " · "+price.toFixed(4)+" "+currencies[0]+"/kWh"+
        " · "+basis[0]+", "+mcTr("reference price, not an invoice")));
      svg.append(circle);
    }
    svg.append(mcSVG("text",{x:950,y:top+2,"text-anchor":"end",
      "font-size":11},hi.toFixed(3)));
    svg.append(mcSVG("text",{x:950,y:bottom+4,"text-anchor":"end",
      "font-size":11},lo.toFixed(3)));
  }
  const now=Date.now();
  if(now>=from&&now<until){
    const at=x0+(now-from)/(until-from)*width;
    svg.append(mcSVG("line",{x1:at,y1:top,x2:at,y2:bottom,
      stroke:"var(--warning-color,#b76b64)","stroke-width":2}));
    svg.append(mcSVG("text",{x:at+3,y:top-6,"font-size":10},mcTr("Now")));
  }
  for(let i=0;i<=4;i++){
    const stamp=new Date(from+(until-from)*i/4);
    svg.append(mcSVG("text",{
      x:x0+i*width/4,y:225,
      "text-anchor":i===0?"start":i===4?"end":"middle",
      "font-size":11
    },stamp.toLocaleString(undefined,{timeZone:data.timezone||"UTC",
      weekday:"short",hour:"2-digit",minute:"2-digit"})));
  }
  const plot=mcEl("div","chart");plot.append(svg);wrapper.append(plot);
  const legend=mcEl("div","legend");
  for(const name of ["Proposed","Accepted","Measured"]){
    legend.append(mcEl("span","",mcTr(name)));
  }
  legend.append(mcEl("span","",priceValues.length?
    basis[0]+" · "+currencies[0]+"/kWh":mcTr("Price unavailable")));
  wrapper.append(legend);
  if(priceReady&&priceValues.length&&priceValues.length<count)
    wrapper.append(mcEl("p","muted small",
      mcTr("Price intervals incomplete; missing periods are not zero")));
  const future=slots.filter(row=>visible.has(row.charger_id)&&
    Date.parse(row.start)>=Date.now()&&typeof row.proposed_power_kw==="number"&&
    Number.isFinite(row.proposed_power_kw)&&row.proposed_power_kw>=0);
  if(future.length){
    const kwh=future.reduce((sum,row)=>sum+(
      typeof row.proposed_energy_kwh==="number"?
        row.proposed_energy_kwh:row.proposed_power_kw/4),0);
    const chargers=new Set(future.map(row=>row.charger_id));
    wrapper.append(mcEl("p","small",mcTr("Still planned")+" · "+
      kwh.toFixed(2)+" kWh · "+chargers.size+" "+
      mcTr(chargers.size===1?"charger":"chargers")));
  }
  if(!values.length)wrapper.append(mcEl("p","muted small",
    mcTr("No qualified physical or planned power in this period")));
  return wrapper;
}

// A schema-aligned read-only projection of the ONE persisted Config Entry.
// Native entity controls and Options Flow below stay the only real writers.
const MC_OWNER_GROUPS = {
  controller: [
    ["Identity & strategy",[
      "id","name","mode","max_parallel","max_power_kw",
      "phase_limits_a","plan_label_mode","plan_color_by",
      "show_indicative_forecast"
    ]],
    ["Energy & tariff sources",[
      "price_entity","current_price_entity","export_price_entity",
      "solar_entity","solar_source_kind","solar_power_entity",
      "solar_surplus_entity","home_power_entity","grid_power_entity",
      "grid_power_direction","site_power_entity","binding_entity"
    ]]
  ],
  asset: [
    ["Vehicle identity & lifetime",[
      "id","name","kind","temporary","expires_at","plan_color"
    ]],
    ["Goal & timing",[
      "target_soc","requested_kwh","requested_duration_minutes",
      "requested_budget_amount","requested_budget_currency",
      "ready_by","ready_by_repeat","ready_by_weekdays",
      "charging_windows","earliest_start_at","expected_connection_at"
    ]],
    ["Price & charging decisions",[
      "continuous_charging","minimum_soc_pct","low_soc_trigger_pct",
      "maximum_price_per_kwh","price_currency","low_price_trigger_per_kwh",
      "opportunistic_kind","opportunistic_level_pct","priority"
    ]],
    ["Battery & source references",[
      "soc_entity","soc_stale_entity",
      "vehicle_control_entity","vehicle_current_entity",
      "capacity_kwh","max_charge_kw","charge_efficiency"
    ]]
  ],
  charger: [
    ["Identity & ownership",[
      "id","name","kind","asset","plan_color",
      "control_owner","physical_commissioned"
    ]],
    ["Connection & meter sources",[
      "control_entity","connected_entity","connected_states",
      "disconnected_states","power_entity","energy_entity",
      "session_entity","current_control_entity","current_readback_entity"
    ]],
    ["Electrical hardware & circuit",[
      "rated_power_kw","phase_count","phase_ids","voltage_v",
      "min_current_a","max_current_a","current_step_a","fixed_current_a",
      "circuit_id","circuit_limit_a","min_charging_power_kw",
      "max_charging_power_kw"
    ]]
  ]
};
const MC_OWNER_NAMES = {
  id:"Object ID",name:"Name",kind:"Type",asset:"Assigned vehicle",
  mode:"Charging mode",max_parallel:"Simultaneous chargers",
  max_power_kw:"Site power ceiling",phase_limits_a:"Maximum per-phase current",
  plan_label_mode:"Plan labels",plan_color_by:"Colors represent",
  show_indicative_forecast:"Show unreserved forecast",
  price_entity:"Future tariff interval source",
  current_price_entity:"Current import price source",
  export_price_entity:"Current export price source",
  solar_entity:"Solar interval source",solar_source_kind:"Solar strategy",
  solar_power_entity:"Solar production sensor",
  solar_surplus_entity:"Available solar surplus sensor",
  home_power_entity:"Home consumption sensor",
  grid_power_entity:"Grid import/export sensor",
  grid_power_direction:"Grid sensor sign",
  site_power_entity:"Site capacity meter",
  binding_entity:"Power envelope source",
  temporary:"Temporary guest",expires_at:"Guest expires",
  plan_color:"Timeline color",target_soc:"Battery target",
  requested_kwh:"Extra energy goal",
  requested_duration_minutes:"Charging duration goal",
  requested_budget_amount:"Indicative budget goal",
  requested_budget_currency:"Budget currency",
  ready_by:"One-time Ready By",
  ready_by_repeat:"Ready By frequency",
  ready_by_weekdays:"Specific weekday Ready By times",
  charging_windows:"Allowed charging time windows",
  earliest_start_at:"Earliest charging start",
  expected_connection_at:"Expected connection time",
  continuous_charging:"Require continuous charging",
  minimum_soc_pct:"Minimum battery priority",
  low_soc_trigger_pct:"Early low-battery trigger",
  maximum_price_per_kwh:"Maximum price per kWh",
  price_currency:"Tariff currency",
  low_price_trigger_per_kwh:"Immediate low-price trigger",
  opportunistic_kind:"Opportunistic strategy",
  opportunistic_level_pct:"Opportunistic percentage",
  priority:"Vehicle charging priority",
  soc_entity:"Battery SoC sensor",
  soc_stale_entity:"Battery freshness sensor",
  vehicle_control_entity:"Vehicle-native command",
  vehicle_current_entity:"Vehicle-native current setting",
  capacity_kwh:"Usable battery capacity",
  max_charge_kw:"Vehicle charging limit",
  charge_efficiency:"Charging efficiency",
  control_owner:"Physical command owner",
  physical_commissioned:"Physical commissioning",
  control_entity:"Native Charger control switch",
  connected_entity:"Cable/connection sensor",
  connected_states:"Connected sensor states",
  disconnected_states:"Disconnected sensor states",
  power_entity:"Actual Charger power meter",
  energy_entity:"Cumulative Charger energy meter",
  session_entity:"Native session sensor",
  current_control_entity:"Current setpoint Number",
  current_readback_entity:"Actual current sensor",
  rated_power_kw:"Rated Charger power",
  phase_count:"Connected phase count",
  phase_ids:"Connected phases",voltage_v:"Nominal voltage",
  min_current_a:"Hardware minimum current",
  max_current_a:"Hardware maximum current",
  current_step_a:"Supported current step",
  fixed_current_a:"Fixed current when connected",
  circuit_id:"Supply circuit",circuit_limit_a:"Circuit breaker limit",
  min_charging_power_kw:"Configured minimum charging power",
  max_charging_power_kw:"Configured maximum charging power"
};
const MC_OWNER_UNITS={
  max_power_kw:" kW",rated_power_kw:" kW",max_charge_kw:" kW",
  min_charging_power_kw:" kW",max_charging_power_kw:" kW",
  capacity_kwh:" kWh",requested_kwh:" kWh",
  requested_duration_minutes:" min",maximum_price_per_kwh:" /kWh",
  low_price_trigger_per_kwh:" /kWh",min_current_a:" A",
  max_current_a:" A",fixed_current_a:" A",current_step_a:" A",
  circuit_limit_a:" A",voltage_v:" V",target_soc:"%",
  minimum_soc_pct:"%",low_soc_trigger_pct:"%",opportunistic_level_pct:"%"
};
function mcOwnerReadValue(value,field,timeZone){
  if(value===undefined||value===null||value==="")return mcTr("Not configured");
  if(typeof value==="boolean")return mcTr(value?"Yes":"No");
  if(Array.isArray(value))return value.length?value.join(", "):mcTr("Not configured");
  if(typeof value==="object"){
    const pairs=Object.entries(value);
    if(!pairs.length)return mcTr("Not configured");
    return pairs.map(([key,v])=>{
      const detail=typeof v==="object"&&v!==null?
        (v.start&&v.end?v.start+"–"+v.end:
          Object.entries(v).map(([a,b])=>a+": "+b).join(", ")):
        String(v);
      return key.toUpperCase()+": "+detail;
    }).join(" · ");
  }
  if(/^(ready_by|earliest_start_at|expected_connection_at|expires_at)$/.test(field))
    return mcTime(value,timeZone);
  const unit=MC_OWNER_UNITS[field]||"";
  return String(value)+unit;
}

class RobotixMultiChargeCard extends HTMLElement {
  constructor(){
    super();
    this.attachShadow({mode:"open"});
    this._tab="Overview";
    this._day="today";
    this._filter="";
    this._open="";
    this._settingsOpen="";
    this._data=null;
    this._error="";
    this._last=0;
    this._loading=false;
    this._commandBusy=false;
    this._commandFeedback={};
    // Local, unsubmitted form values only; not an execution or settings store.
    this._manualDrafts={};
    this._calendarDrafts={};
    this._windowsOpen="";
    this._settingsBusy=false;
    this._settingsFeedback=null;
    this._pendingSettings=null;
    this._assetEditor="";
    this._assignmentEditor="";
    this._goalDrafts={};
    this._scheduleEditor="";
    this._fieldSequence=0;
    this._refreshTimer=null;
    this._refreshPending=false;
    this._pendingNative=null;
    this._yamlFlow=null;
    this._yamlBusy=false;
    this._yamlError="";
    this._yamlText="";
    this._yamlMode="replace";
  }
  canManage(){return this._hass?.user?.is_admin===true;}
  canEditSettings(){return this.canManage()&&!this._data?.configuration_managed_by_yaml;}
  watchedEntities(){
    const data=this._data||{},cfg=data.configuration||{},refs=data.preference_entities||{};
    const ids=new Set();
    for(const row of [cfg.controller,...(cfg.assets||[]),...(cfg.chargers||[])]){
      for(const [key,value] of Object.entries(row||{}))
        if(key.endsWith("_entity")&&typeof value==="string")ids.add(value);
    }
    for(const row of [refs.controller,...Object.values(refs.assets||{}),
                      ...Object.values(refs.chargers||{})])
      for(const value of Object.values(row||{}))
        if(typeof value==="string"&&value.includes("."))ids.add(value);
    return ids;
  }
  scheduleSourceRefresh(){
    if(this._refreshTimer!==null)return;
    this._refreshTimer=setTimeout(()=>{
      this._refreshTimer=null;
      if(this._loading){this._refreshPending=true;return;}
      this._last=0;this.load();
    },350);
  }
  disconnectedCallback(){
    if(this._refreshTimer!==null)clearTimeout(this._refreshTimer);
    this._refreshTimer=null;
    if(this._yamlFlow)void this.cancelYamlEditor();
  }
  setConfig(config){this._cardConfig=config||{};this.render();}
  getCardSize(){return 10;}
  set hass(value){
    const before=this._hass;
    this._hass=value;
    if(this._yamlFlow&&!this.canEditSettings())void this.cancelYamlEditor();
    if(this._pendingNative&&value?.states?.[this._pendingNative.entity]?.state===
        this._pendingNative.expected){
      this._pendingNative=null;
      this._settingsFeedback={status:"confirmed",message:"Saved"};
    }
    const changed=before&&this._data&&[...this.watchedEntities()].some(
      id=>before.states?.[id]!==value.states?.[id]
    );
    if(changed)this.scheduleSourceRefresh();
    else if(!this._loading&&(!this._last||Date.now()-this._last>60000))this.load();
    else if(this._data)this.render();
  }
  async load(){
    if(!this._hass||this._loading)return;
    this._loading=true;this._error="";this.render();
    try {
      const cmd={type:"robotix_multicharge/get_plan",day:this._day};
      if(this._filter.startsWith("charger:"))cmd.charger_id=this._filter.slice(8);
      if(this._filter.startsWith("asset:"))cmd.asset_id=this._filter.slice(6);
      const nextData=await this._hass.callWS(cmd);
      if(this._data?.configuration_revision&&
         this._data.configuration_revision!==nextData.configuration_revision)
        this._manualDrafts={};
      const chargerIds=new Set((nextData.configuration?.chargers||[]).map(c=>c.id));
      for(const id of Object.keys(this._manualDrafts))
        if(!chargerIds.has(id))delete this._manualDrafts[id];
      this._data=nextData;
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
    }finally{
      this._loading=false;this.render();
      if(this._refreshPending){
        this._refreshPending=false;this.scheduleSourceRefresh();
      }
    }
  }
  async command(charger,action,manualRequest=null){
    if(this._commandBusy||!this._hass||!this.canManage())return;
    this._commandBusy=true;
    this._commandFeedback[charger]={status:"requested",reason:"Pending"};
    this.render();
    try {
      const request={type:"robotix_multicharge/command",
                     charger_id:charger,action};
      if(manualRequest)Object.assign(request,manualRequest);
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
    if(this._settingsBusy||!this._hass||!this._data||!this.canEditSettings())return;
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
      const detail=String(error?.message||error?.code||"");
      const reason=detail.includes("CHARGER_BUSY_STOP_FIRST")?
        "Stop charging before changing charger":
        detail.includes("CHARGER_HAS_OTHER_ASSET")?
          "Unassign the other vehicle first":
        detail.includes("STALE_SETTINGS_REFRESH")?
          "Settings changed; refresh and retry":"Unavailable";
      this._settingsFeedback={status:"rejected",message:reason};
    }finally{
      this._settingsBusy=false;
      if(this._pendingSettings)await this.load();
      this.render();
    }
  }
  async openYamlEditor(){
    if(this._yamlBusy||this._yamlFlow||!this.canEditSettings()||
       typeof this._hass?.callApi!=="function")return;
    this._yamlBusy=true;this._yamlError="";this.render();
    let pending=null;
    try{
      const entries=await this._hass.callApi("GET","config/config_entries/entry");
      const matches=(Array.isArray(entries)?entries:[]).filter(x=>
        x.domain==="robotix_multicharge");
      if(matches.length!==1)throw Error("Exactly one MultiCharge Config Entry required");
      pending=await this._hass.callApi("POST","config/config_entries/options/flow",
        {handler:matches[0].entry_id});
      if(pending?.type!=="menu"||pending.step_id!=="init"||
         typeof pending.flow_id!=="string")
        throw Error("Unexpected Home Assistant Options Flow menu");
      const flow=await this._hass.callApi("POST",
        "config/config_entries/options/flow/"+encodeURIComponent(pending.flow_id),
        {next_step_id:"yaml"});
      if(flow?.type!=="form"||flow.step_id!=="yaml")
        throw Error("Home Assistant rejected YAML edit");
      this._yamlFlow=flow;
      const input=(flow.data_schema||[]).find(x=>x.name==="yaml_text");
      const mode=(flow.data_schema||[]).find(x=>x.name==="mode");
      this._yamlText=String(input?.description?.suggested_value??input?.default??"");
      this._yamlMode=String(mode?.default||"replace");
      this._settingsOpen="Advanced & YAML";
      pending=null;
    }catch(error){
      this._yamlError=String(error?.message||"Unable to open native configuration editor");
      if(pending?.flow_id)try{await this._hass.callApi("DELETE",
        "config/config_entries/options/flow/"+encodeURIComponent(pending.flow_id));}catch(_){}
    }finally{this._yamlBusy=false;this.render();}
  }
  async cancelYamlEditor(){
    const flow=this._yamlFlow;
    this._yamlFlow=null;this._yamlError="";this._yamlText="";
    if(flow?.flow_id&&typeof this._hass?.callApi==="function"){
      try{await this._hass.callApi("DELETE",
        "config/config_entries/options/flow/"+encodeURIComponent(flow.flow_id));}
      catch(_){}
    }
    this.render();
  }
  async advanceYamlEditor(payload){
    if(!this._yamlFlow||this._yamlBusy||!this.canEditSettings()||
       typeof this._hass?.callApi!=="function")return;
    const current=this._yamlFlow;
    if(current.type!=="form")return;
    this._yamlBusy=true;this._yamlError="";this.render();
    try{
      const next=await this._hass.callApi("POST",
        "config/config_entries/options/flow/"+encodeURIComponent(current.flow_id),
        payload);
      if(next?.type==="create_entry"){
        this._yamlFlow=null;this._yamlText="";
        this._settingsFeedback={status:"accepted_unconfirmed",
          message:"Home Assistant save accepted; verifying readback"};
        this._last=0;
        await this.load();
      }else if(next?.type==="form"&&
               ["yaml","yaml_review"].includes(next.step_id)){
        this._yamlFlow=next;
        if(next.step_id==="yaml"&&current.step_id==="yaml_review")
          this._yamlError="";
        if(Object.keys(next.errors||{}).length){
          const source=next.description_placeholders?.note||
            next.description_placeholders?.summary||"";
          const detail=source.includes("Validation:")?
            source.split("Validation:").pop().trim():
            Object.values(next.errors).join(", ");
          this._yamlError="YAML rejected: "+detail;
        }
      }else throw Error("Unexpected native configuration response");
    }catch(error){
      this._yamlError=String(error?.message||"Configuration not accepted");
      // Preserve the user's YAML draft for retry; do not claim it was saved.
    }finally{this._yamlBusy=false;this.render();}
  }
  yamlEditor(container){
    if(!this._yamlFlow)return;
    const flow=this._yamlFlow;
    const area=mcEl("section","yaml-editor");
    const heading=mcEl("h3","",flow.step_id==="yaml_review"?
      "Review configuration changes":"YAML configuration (advanced)");
    area.append(heading);
    area.append(mcEl("p","muted small",flow.step_id==="yaml_review"?
      "Nothing is saved until you confirm. No charging commands are sent.":
      "Edit current Config Entry YAML. Keep existing IDs. Home Assistant validates the full draft."));
    if(this._yamlError){
      const msg=mcEl("p","yaml-error",this._yamlError);
      msg.setAttribute("role","alert");area.append(msg);
    }
    if(flow.step_id==="yaml"){
      const field=mcEl("div","field");
      const label=mcEl("label","",mcTr("Update mode"));
      const mode=mcEl("select");
      mode.setAttribute("aria-label","Update mode");
      for(const [value,description] of [
        ["replace","Complete configuration (replace omitted entries)"],
        ["merge","Scoped changes (preserve other entries)"]]){
        const opt=mcEl("option","",description);
        opt.value=value;mode.append(opt);
      }
      mode.value=this._yamlMode;
      mode.addEventListener("change",()=>{this._yamlMode=mode.value;});
      const edit=mcEl("textarea");
      edit.setAttribute("aria-label","MultiCharge YAML configuration");
      edit.value=this._yamlText;
      edit.rows=18;
      edit.spellcheck=false;
      edit.addEventListener("input",()=>{this._yamlText=edit.value;});
      field.append(label,mode,mcEl("label","",mcTr("Configuration YAML")),edit);
      area.append(field);
      const buttons=mcEl("div","yaml-actions");
      const review=mcButton("Continue / review",()=>this.advanceYamlEditor({
        mode:this._yamlMode,yaml_text:this._yamlText}));
      review.disabled=this._yamlBusy;
      buttons.append(review,mcButton("Cancel",()=>this.cancelYamlEditor()));
      area.append(buttons);
    }else if(flow.step_id==="yaml_review"){
      const summary=flow.description_placeholders?.summary||"Review changes in Home Assistant";
      area.append(mcEl("pre","config-code",summary));
      const actions=mcEl("div","yaml-actions");
      const confirm=mcButton("Apply reviewed changes",()=>this.advanceYamlEditor({confirm:true}));
      confirm.disabled=this._yamlBusy;
      const back=mcButton("Back to YAML",()=>this.advanceYamlEditor({edit_again:true}));
      back.disabled=this._yamlBusy;
      actions.append(confirm,back,mcButton("Cancel",()=>this.cancelYamlEditor()));
      area.append(actions);
    }
    container.append(area);
  }
  ownerEntity(scope,uid,field){
    const prefs=this._data?.preference_entities||{};
    const group=scope==="controller"?prefs.controller:
      scope==="asset"?prefs.assets?.[uid]:prefs.chargers?.[uid];
    return group?.[field]||null;
  }
  async nativeSelect(scope,uid,field,option){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||!entity||!this._hass?.callService){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Updating"};
    this.render();
    try{
      const expected=field==="mode"?MC_MODE_SELECT[option]||option:option;
      await this._hass.callService("select","select_option",{
        entity_id:entity,option:expected
      });
      this._pendingNative={entity,expected};
      this._last=0;
      await this.load();
      if(this._hass?.states?.[entity]?.state===expected){
        this._pendingNative=null;
        this._settingsFeedback={status:"confirmed",message:"Saved"};
      }else{
        this._settingsFeedback={status:"accepted_unconfirmed",message:"Updating"};
      }
    }catch(error){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
    }finally{this._settingsBusy=false;this.render();}
  }
  async nativeText(scope,uid,field,value){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||!entity||!this._hass?.callService||this._settingsBusy)
      return;
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Updating"};
    try{
      await this._hass.callService("text","set_value",{entity_id:entity,value});
      this._pendingNative={entity,expected:value};
      this._last=0;await this.load();
      const observed=this._hass?.states?.[entity]?.state;
      const confirmed=observed===value;
      if(confirmed)this._pendingNative=null;
      this._settingsFeedback={
        status:confirmed?"confirmed":"accepted_unconfirmed",
        message:confirmed?"Saved":"Awaiting native state"
      };
    }catch(error){
      this._settingsFeedback={status:"rejected",
        message:String(error?.message||"Window settings rejected")};
    }finally{this._settingsBusy=false;this.render();}
  }
  async nativeButton(scope,uid,field){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canManage()||!entity||!this._hass?.callService){
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
  async nativeNumber(scope,uid,field,value){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||this._settingsBusy||!entity||
       typeof this._hass?.callService!=="function"||!Number.isFinite(value)){
      this._settingsFeedback={status:"rejected",message:"Unsupported number value"};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Applying"};
    this.render();
    try{
      await this._hass.callService("number","set_value",{
        entity_id:entity,value
      });
      this._last=0;
      await this.load();
      const state=this._hass?.states?.[entity]?.state;
      const confirmed=state!==undefined&&state!=="unknown"&&
        state!=="unavailable"&&Math.abs(Number(state)-value)<0.00001;
      // An EVSE may quantize a requested kW into real physical Amp steps:
      // never claim a requested setpoint equals physically measured power.
      this._settingsFeedback={
        status:confirmed?"confirmed":"accepted_unconfirmed",
        message:confirmed?"Saved":"Awaiting native HA/EVSE readback"
      };
      if(!confirmed&&field!=="set_charging_power_kw")
        this._pendingNative={entity,expected:String(value)};
    }catch(error){
      this._settingsFeedback={status:"rejected",message:String(
        error?.message||"Number rejected by Home Assistant"
      )};
    }finally{
      this._settingsBusy=false;this.render();
    }
  }
  nativeNumberEditor(container,scope,uid,field,label,fallback,unit=""){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||!entity)return;
    const native=this._hass?.states?.[entity];
    const state=native?.state;
    const observed=state!==undefined&&state!=="unavailable"&&
      state!=="unknown"&&state!==""&&Number.isFinite(Number(state))?
      Number(state):fallback;
    const row=mcEl("div","field native-number");
    const labelNode=mcEl("label","",mcTr(label)+(unit?" ("+unit+")":""));
    const control=mcEl("div","row");
    const input=mcEl("input");
    input.setAttribute("type","number");
    input.setAttribute("aria-label",mcTr(label));
    const controlId="multicharge-native-number-"+(this._fieldSequence++);
    input.setAttribute("id",controlId);
    labelNode.setAttribute("for",controlId);
    input.value=observed===undefined||observed===null?"":String(observed);
    const attr=native?.attributes||{};
    if(Number.isFinite(Number(attr.min))&&attr.min!==undefined)
      input.setAttribute("min",String(attr.min));
    if(Number.isFinite(Number(attr.max))&&attr.max!==undefined)
      input.setAttribute("max",String(attr.max));
    input.setAttribute("step",String(attr.step||0.01));
    const apply=mcButton(mcTr("Apply"),()=>{
      const value=Number(input.value);
      if(!input.value.trim()||!Number.isFinite(value)){
        this._settingsFeedback={status:"rejected",message:"Number required"};
        this.render();return;
      }
      void this.nativeNumber(scope,uid,field,value);
    });
    apply.disabled=this._settingsBusy||native?.state==="unavailable";
    control.append(input,apply);row.append(labelNode,control);
    container.append(row);
  }
  nativeRepeatEditor(container,asset){
    const field="ready_by_repeat",entity=this.ownerEntity("asset",asset.id,field);
    const mode=this._calendarDrafts[asset.id]||
      (asset.ready_by_repeat==="weekly"?"specific_days":asset.ready_by_repeat||"none");
    if(!this.canEditSettings()||!entity)return;
    container.append(mcEl("h4","specific-day-calendar",mcTr("Charging days")));
    const choice=this.field(container,mcTr("Charging schedule"),mode,null,[
      ["none",mcTr("Once")],["daily",mcTr("Daily")],
      ["specific_days",mcTr("Specific days")]
    ]);
    choice.disabled=this._settingsBusy;
    choice.addEventListener("change",()=>{
      this._calendarDrafts[asset.id]=choice.value;
      if(choice.value==="specific_days" && !asset.ready_by_weekdays){
        this.render();return; // first explicit weekday selection commits both
      }
      if(choice.value==="daily" && !asset.ready_by){
        this._settingsFeedback={status:"rejected",
          message:"Set Ready By before selecting Daily"};
        this.render();return;
      }
      void this.nativeSelect("asset",asset.id,field,choice.value);
      this.render();
    });
    if(mode==="daily"&&!asset.ready_by)
      container.append(mcEl("p","muted small",mcTr("Set Ready By first to enable recurring charging")));
    if(mode==="specific_days"){
      const days=mcEl("div","details specific-days");
      for(const [day,label] of Object.entries(MC_DAY_NAMES)){
        const owned=this.ownerEntity("asset",asset.id,"ready_day_"+day);
        if(!owned)continue;
        const observed=this._hass?.states?.[owned]?.state;
        const saved=asset.ready_by_weekdays?.[day]||
          (observed && observed!=="unknown" && observed!=="unavailable"?
           observed:"off");
        const select=this.field(days,mcTr(label),saved,null,[
          ["off",mcTr("No day selected")],
          ...MC_CLOCKS.map(hour=>[hour,hour])
        ]);
        select.disabled=this._settingsBusy;
        select.addEventListener("change",()=>{
          void this.nativeSelect("asset",asset.id,"ready_day_"+day,select.value);
          delete this._calendarDrafts[asset.id];
        });
      }
      container.append(days);
    }
    this.nativeChargingWindowsEditor(container,asset);
  }
  nativeChargingWindowsEditor(container,asset){
    const available=Object.values(MC_DAY_NAMES).length;
    if(!available)return;
    const button=mcButton(mcTr("Allowed charging times"),()=>{
      this._windowsOpen=this._windowsOpen===asset.id?"":asset.id;
      this.render();
    });
    container.append(button);
    if(this._windowsOpen!==asset.id)return;
    const panel=mcEl("div","details");
    for(const [day,label] of Object.entries(MC_DAY_NAMES)){
      const field="charging_window_"+day;
      if(!this.ownerEntity("asset",asset.id,field))continue;
      const window=asset.charging_windows?.[day];
      const enabled=this.field(panel,mcTr(label),
        window?"on":"off",null,[
          ["off",mcTr("Window disabled")],["on",mcTr("Window enabled")]
        ]);
      const start=this.field(panel,mcTr(label)+" · "+mcTr("Start hour"),
        window?.start||"22:00","time");
      const end=this.field(panel,mcTr(label)+" · "+mcTr("End hour"),
        window?.end||"06:00","time");
      const save=()=>{
        if(enabled.value==="on"&&(!start.value||!end.value||
                                   start.value===end.value)){
          this._settingsFeedback={status:"rejected",
             message:"Start and end hours must differ"};
          this.render();return;
        }
        void this.nativeText("asset",asset.id,field,
          enabled.value==="on"?start.value+"-"+end.value:"");
      };
      for(const fieldNode of [enabled,start,end]){
        fieldNode.disabled=this._settingsBusy;
        fieldNode.addEventListener("change",save);
      }
    }
    container.append(panel);
  }
  openNative(scope,uid,field){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||!entity){this._settingsFeedback={status:"rejected",message:"Unavailable"};this.render();return;}
    this.dispatchEvent(new CustomEvent("hass-more-info",{
      bubbles:true,composed:true,detail:{entityId:entity}
    }));
  }
  ownerColorControl(container,scope,row){
    const palette=this._data?.plan_palette||{};
    const entity=this.ownerEntity(scope,row.id,"plan_color");
    const options=Object.keys(palette).map(key=>[key,mcTr(key)]);
    const pick=this.field(container,"Plan color",row.plan_color,null,options);
    pick.disabled=!this.canEditSettings()||!entity||this._settingsBusy;
    pick.addEventListener("change",()=>this.nativeSelect(
      scope,row.id,"plan_color",pick.value
    ));
    return pick;
  }
  field(container,title,value,type,choices){
    const wrapper=mcEl("div","field"),label=mcEl("label","",title);
    const input=mcEl(choices?"select":"input");
    const id="multicharge-"+title.toLowerCase().replace(/[^a-z0-9]+/g,"-")+"-"+(this._fieldSequence++);
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
      result.status==="confirmed"?"Saved":
      result.status==="rejected"?(result.message||"Unavailable"):"Pending");
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
    if(!this.canManage())return;
    const link=mcEl("a","action",mcTr("Configure in Home Assistant"));
    link.href="/config/integrations/integration/robotix_multicharge";
    link.setAttribute("aria-label",mcTr("Home Assistant"));
    container.append(link);
  }
  render(){
    mcLanguage=String(this._hass?.locale?.language||this._hass?.language||"en").slice(0,2).toLowerCase();
    if(!this.shadowRoot)return;
    const root=this.shadowRoot;root.replaceChildren();
    this._fieldSequence=0;
    const style=mcEl("style");style.textContent=MC_STYLE;root.append(style);
    const shell=mcEl("section","root");
    const head=mcEl("div","heading");const heading=mcEl("div");
    heading.append(mcEl("h2","","MultiCharge"));
    head.append(heading,mcButton("Refresh",()=>{this._last=0;this.load();}));
    shell.append(head);
    const tabs=mcEl("nav","tabs");tabs.setAttribute("aria-label","MultiCharge views");
    for(const item of MC_TABS){
      const btn=mcButton(item,()=>{
        if(item!=="Settings"&&this._yamlFlow)void this.cancelYamlEditor();
        this._tab=item;this.render();
      });
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
    const priceKind=priced.basis==="variable_reference"?
      "Variable reference price":priced.basis==="spot"?
        "Spot price":"Current price";
    const powers=chargers.map(x=>(observations[x.id]||{}).power_kw);
    const complete=powers.length>0&&powers.every(x=>x&&x.quality==="ok"&&typeof x.value==="number");
    const active=powers.filter(x=>x&&x.quality==="ok"&&x.value>0).length;
    const metrics=mcEl("div","grid");
    for(const [key,value] of [
      ["Active chargers",!chargers.length?"0":complete?String(active):"Unknown"],
      ["Actual power",complete?(powers.reduce((sum,x)=>sum+x.value,0).toFixed(2)+" kW"):"Unknown"],
      [priceKind,priceLabel]
    ]){const el=mcEl("div","metric");el.append(mcEl("p","muted small",mcTr(key)),mcEl("div","value",value));metrics.append(el);}
    container.append(metrics);
    const mode=(c.controller||{}).mode||"Off";
    const chips=mcEl("div","chips");chips.append(mcEl("p","muted",mcTr("Charging mode")+" · "+mode));
    for(const item of this.canEditSettings()?MC_MODES:[]){
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
      const controls=mcEl("div","overview-actions");
      controls.append(mcButton(mcTr("Charging plan"),()=>{
        this._filter="asset:"+a.id;
        this._tab="Charging Plan";this._last=0;this.load();
      }));
      if(this.canEditSettings()){
        controls.append(mcButton(mcTr("Set charging goal"),()=>{
          this._tab="Chargeable Assets";this._open="";
          this.render();
        }));
        controls.append(mcButton(mcTr("Schedule charging"),()=>{
          this._tab="Chargeable Assets";this._scheduleEditor=a.id;this.render();
        }));
      }
      if(charger&&this.canManage()){
        const physical=(observations[charger.id]||{}).power_kw;
        const capabilities=(d.command_capabilities||{})[charger.id]||{};
        if(capabilities.stop_allowed&&physical?.quality==="ok"&&
            typeof physical.value==="number"&&physical.value>0){
          const stop=mcButton(mcTr("Stop charging"),()=>
            this.command(charger.id,"stop"));
          stop.disabled=this._commandBusy;
          controls.append(stop);
        }
      }
      card.append(controls);
      container.append(card);
    }
    if(!assets.length&&chargers.length)this.notice(container,"No vehicles",false);
    if(this.canEditSettings()){
      const add=mcButton(mcTr("Add guest or vehicle"),()=>{
        this._tab="Chargeable Assets";this._assetEditor="new";this.render();
      });
      container.append(add);
    }
    const next=mcEl("div","card");next.append(mcEl("h3","","Next action"));
    next.append(mcEl("p","",!chargers.length?"Configure a charger to begin":d.status==="unavailable"?"Not ready":"Plan"));
    if(!chargers.length)this.configure(next);
    const reasons=Object.entries(d.reasons||{}).filter(([key,val])=>val!=="PROPOSED");
    if(reasons.length)next.append(mcEl("p","muted small",reasons.map(([key,val])=>key+": "+mcReason(val)).slice(0,4).join(" · ")));
    container.append(next);
  }
  plan(container){
    const d=this._data,c=d.configuration||{},controller=c.controller||{};
    const cars=c.assets||[],chargers=c.chargers||[];
    const labelMode=controller.plan_label_mode||"both";
    const colorBy=controller.plan_color_by||"vehicle";
    const forecastVisible=controller.show_indicative_forecast!==false;
    this.title(container,"Charging plan");
    if(!chargers.length){
      this.notice(container,"No charging points",false);
      this.configure(container);
      return;
    }
    const day=mcEl("div","controls");
    for(const chosen of ["today","tomorrow","both"]){
      const b=mcButton(chosen==="today"?"Today":chosen==="tomorrow"?"Tomorrow":"48h",()=>{
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
      select.disabled=!this.canEditSettings()||this._settingsBusy||!this.ownerEntity("controller",controller.id,setting);
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
    container.append(mcCombinedChargingChart(d,shown,rows,measured));
    container.append(mcEl("h3","",mcTr("Charging per vehicle and charger")));
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
      const identity=(d.connection_identity||{})[charger.id];
      const verified=selected&&identity?.asset_id===selected.id;
      const plugged=source&&source.quality==="ok"?
        source.value?(verified?mcTr("Connected")+" · "+selected.name:
          mcTr("Connected")+" · "+mcTr("Vehicle unknown")):
        mcTr("Disconnected"):mcTr("Connection unknown");
      const fullName=labelMode==="vehicle"?vehicleLabel:
        labelMode==="charger"?charger.name:vehicleLabel+" · "+charger.name;
      const color=colorBy==="charger"?
        mcOwnerColor("charger",charger.id,c,d.plan_palette):
        mcOwnerColor("asset",charger.asset,c,d.plan_palette);
      const lhs=mcEl("div","plan-key");
      const swatch=mcEl("span","plan-swatch");swatch.style.background=color;
      lhs.append(swatch,mcEl("strong","",fullName));
      label.append(lhs,mcEl("span","muted small",plugged));card.append(label);
      const readback=(d.observations||{}).assets?.[selected?.id]||{};
      const next=activeRows.find(item=>typeof item.proposed_power_kw==="number"&&
        Date.parse(item.end)>Date.now());
      const reason=(d.reasons||{})[charger.id];
      const shortfall=(d.shortfall_kwh||{})[charger.id];
      const summary=mcEl("p","small lane-summary",
        mcTr("Battery")+" "+mcValue(readback.soc,"%")+" · "+
        mcTr("Target")+" "+(selected?.target_soc===undefined?mcTr("Not set"):
          selected.target_soc+"%")+" · "+mcTr("Ready By")+" "+
        mcTime(readback.next_ready_by?.value||selected?.ready_by,d.timezone)+
        (next?" · "+mcTr("Next charge")+" "+
          mcTime(next.start,d.timezone)+" · "+next.proposed_power_kw+" kW":""));
      card.append(summary);
      if(typeof shortfall==="number"&&shortfall>0)
        card.append(mcEl("p","plan-caution",mcTr("Shortfall")+" · "+
          shortfall.toFixed(2)+" kWh"));
      if(reason&&reason!=="PROPOSED"&&reason!=="TARGET_MET")
        card.append(mcEl("p","plan-caution",mcReason(reason)));
      if(actualRows.some(row=>row.asset_provenance!=="confirmed_closed_session"))
        card.append(mcEl("p","muted small",
          mcTr("Measured power is attributed to this charger; vehicle may be unknown")));
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
  // One visible resident-readable goal control, one authorized atomic
  // settings transaction. Unsubmitted drafts are local form state only.
  assetGoalEditor(card,asset){
    const kind=asset.requested_budget_amount!==undefined?"budget":
      asset.requested_duration_minutes!==undefined?"duration":
      asset.requested_kwh!==undefined?"energy":"soc";
    const original=kind==="budget"?asset.requested_budget_amount:
      kind==="duration"?asset.requested_duration_minutes:
      kind==="energy"?asset.requested_kwh:asset.target_soc;
    const stored=this._goalDrafts[asset.id];
    const draft=stored||{mode:kind,value:original===undefined?"":String(original)};
    if(!this.canEditSettings())return;
    const form=mcEl("section","quick-goal");
    form.append(mcEl("h4","",mcTr("Set charging goal")));
    const controls=mcEl("div","goal-controls");
    const goal=this.field(controls,mcTr("I want to charge to"),
      draft.mode,null,[
        ["soc",mcTr("Battery target (%)")],
        ["energy",mcTr("Extra energy (kWh)")],
        ["duration",mcTr("Charging time (minutes)")],
        ["budget",mcTr("Charging budget (€)")]
      ]);
    const amount=this.field(controls,mcTr("Amount"),draft.value,"number");
    amount.setAttribute("min",draft.mode==="soc"?"0":"0.01");
    amount.setAttribute("step",draft.mode==="duration"?"1":"0.01");
    goal.disabled=this._settingsBusy;
    amount.disabled=this._settingsBusy;
    goal.addEventListener("change",()=>{
      this._goalDrafts[asset.id]={mode:goal.value,value:""};
      this.render();
    });
    amount.addEventListener("input",()=>{
      this._goalDrafts[asset.id]={mode:goal.value,value:amount.value};
    });
    const action=mcButton(mcTr("Save charging goal"),()=>{
      const number=Number(amount.value);
      if(!amount.value.trim()||!Number.isFinite(number)||
          number<0||(goal.value!=="soc"&&number<=0)||
          (goal.value==="soc"&&number>100)||
          (goal.value==="duration"&&!Number.isInteger(number))||
          (goal.value==="budget"&&number>10000)){
        this._settingsFeedback={status:"rejected",message:"Invalid charging amount"};
        this.render();return;
      }
      const changes={
        requested_kwh:null,requested_duration_minutes:null,
        requested_budget_amount:null,requested_budget_currency:null
      };
      if(goal.value==="soc")changes.target_soc=number;
      if(goal.value==="energy")changes.requested_kwh=number;
      if(goal.value==="duration")changes.requested_duration_minutes=number;
      if(goal.value==="budget"){
        changes.requested_budget_amount=number;
        changes.requested_budget_currency="EUR";
      }
      delete this._goalDrafts[asset.id];
      void this.saveSettings("asset",asset.id,changes,"save");
    });
    action.disabled=this._settingsBusy;
    form.append(controls,action);
    if(draft.mode==="budget")form.append(mcEl("p","muted small",
      mcTr("Indicative energy budget, not a guaranteed electricity bill")));
    card.append(form);
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
      mcPair(card,"Ready By",mcTime(obs.next_ready_by!==undefined?obs.next_ready_by:a.ready_by,d.timezone));
      mcPair(card,"Charger",charger?charger.name:"Not assigned");
      const goal=a.requested_budget_amount!==undefined?
        a.requested_budget_amount+" EUR":
        a.requested_duration_minutes!==undefined?
          a.requested_duration_minutes+" min":
        a.requested_kwh!==undefined?a.requested_kwh+" kWh":
        a.target_soc!==undefined?a.target_soc+"%":mcTr("Not set");
      mcPair(card,mcTr("Charging goal"),goal);
      mcPair(card,mcTr("Charging pattern"),a.continuous_charging?
        mcTr("One continuous charge"):mcTr("Flexible cheapest quarters"));
      if(a.maximum_price_per_kwh!==undefined)mcPair(card,
        mcTr("Price ceiling per kWh"),
        a.maximum_price_per_kwh+" "+(a.price_currency||"")+"/kWh");
      this.assetGoalEditor(card,a);
      if(this.canEditSettings()){
        const calendar=mcButton(
          this._scheduleEditor===a.id?mcTr("Hide charging schedule"):
            mcTr("Schedule charging"),()=>{
            this._scheduleEditor=this._scheduleEditor===a.id?"":a.id;
            this.render();
          });
        calendar.disabled=this._settingsBusy;
        card.append(calendar);
        if(this._scheduleEditor===a.id){
          const schedule=mcEl("div","details schedule-editor");
          schedule.append(mcEl("h4","",mcTr("When should the vehicle be ready?")));
          if(this.ownerEntity("asset",a.id,"ready_by"))
            schedule.append(mcButton(mcTr("Set one-time or daily Ready By"),()=>
              this.openNative("asset",a.id,"ready_by")));
          this.nativeRepeatEditor(schedule,a);
          card.append(schedule);
        }
      }
      if(this.canEditSettings()&&chargers.length){
        const change=mcButton(
          mcTr(charger?"Change charger":"Assign charger"),()=>{
            this._assignmentEditor=this._assignmentEditor===a.id?"":a.id;
            this.render();
          }
        );
        change.disabled=this._settingsBusy;
        card.append(change);
        if(this._assignmentEditor===a.id){
          // A selected Vehicle belongs to exactly one Charger Config Entry
          // field. Do not silently replace a different assigned Vehicle.
          const candidates=chargers.filter(c=>!c.asset||c.asset===a.id);
          const editor=mcEl("div","details assignment-editor");
          editor.append(mcEl("p","muted small",
            "Idle-only reassignment. Stop charging separately before moving a vehicle."));
          if(candidates.length){
            const chooser=mcEl("select");
            chooser.setAttribute("aria-label",mcTr("Select charger"));
            for(const candidate of candidates){
              const option=mcEl("option","",candidate.name);
              option.value=candidate.id;
              chooser.append(option);
            }
            chooser.value=charger?.id||candidates[0].id;
            const apply=mcButton(mcTr("Assign selected charger"),()=>{
              if(!chooser.value||chooser.value===charger?.id)return;
              this.saveSettings("charger",chooser.value,{asset:a.id},"save");
            });
            apply.disabled=this._settingsBusy||
              !chooser.value||chooser.value===charger?.id;
            chooser.addEventListener("change",()=>{
              apply.disabled=this._settingsBusy||
                !chooser.value||chooser.value===charger?.id;
            });
            editor.append(chooser,apply);
          }else editor.append(mcEl("p","muted small","No free charger"));
          if(charger){
            const detach=mcButton(mcTr("Unassign charger"),()=>
              this.saveSettings("charger",charger.id,{asset:null},"save"));
            detach.disabled=this._settingsBusy;
            editor.append(detach);
          }
          editor.append(mcButton(mcTr("Close assignment"),()=>{
            this._assignmentEditor="";this.render();
          }));
          card.append(editor);
        }
      }
      if(this._open===a.id){
        const detail=mcEl("div","details");
        mcPair(detail,"Charging priority",a.priority===undefined?"Not set":a.priority);
        mcPair(detail,"Battery data",obs.soc?(obs.soc.quality+" · "+(a.soc_entity||"manual")):"Unknown");
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"soc_entity")){
          const sourceEdit=mcEl("div","row");
          sourceEdit.append(mcEl("span","muted small",mcTr("Battery source")),
            mcButton(mcTr("Edit"),()=>this.openNative("asset",a.id,"soc_entity")));
          detail.append(sourceEdit);
        }
        mcPair(detail,"Requested energy",a.requested_kwh===undefined?"Not set":a.requested_kwh+" kWh");
        mcPair(detail,"Duration",a.requested_duration_minutes===undefined?"Not set":a.requested_duration_minutes+" min");
        mcPair(detail,mcTr("Charging budget"),
          a.requested_budget_amount===undefined?mcTr("Not set"):
          a.requested_budget_amount+" "+(a.requested_budget_currency||"EUR"));
        if(charger&&a.requested_budget_amount!==undefined){
          const current=(d.active_sessions||{})[charger.id];
          if(current?.budget_quality==="qualified_effective_meter_increments"||
             current?.budget_quality==="conservative_effective_upper_bound"){
            const conservative=current.budget_quality==="conservative_effective_upper_bound";
            mcPair(detail,mcTr(conservative?"Conservative budget upper bound":
              "Indicative variable spending"),
              Number(current.budget_cost||0).toFixed(2)+" "+
              (current.requested_budget_currency||"EUR"));
            mcPair(detail,mcTr(conservative?"Budget remaining (conservative)":
              "Budget remaining"),
              Math.max(0,a.requested_budget_amount-(current.budget_cost||0)).toFixed(2)+
              " "+(current.requested_budget_currency||"EUR"));
          }else if(current?.requested_budget_amount!=null)
            mcPair(detail,mcTr("Budget progress"),mcTr("Unavailable"));
        }
        detail.append(mcEl("h4","",mcTr("Charging preferences")));
        for(const [field,label,unit] of [
          ["target_soc","Charging limit","%"],
          ["requested_kwh","Requested energy","kWh"],
          ["requested_duration_minutes","Requested charging duration","minutes"],
          ["requested_budget_amount","Requested budget (€)","EUR"],
          ["minimum_soc_pct","Minimum charge before price limits","%"],
          ["maximum_price_per_kwh","Price ceiling per kWh","currency/kWh"],
          ["low_price_trigger_per_kwh","Immediate low-price threshold","currency/kWh"],
          ["low_soc_trigger_pct","Immediate low-SoC threshold","%"],
          ["opportunistic_level_pct","Opportunistic percentage","%"],
          ["max_charge_kw","Maximum vehicle charging power","kW"],
          ["priority","Priority",""],
          ["capacity_kwh","Battery capacity","kWh"],
          ["charge_efficiency","Charging efficiency",""]
        ])this.nativeNumberEditor(detail,"asset",a.id,field,label,a[field],unit);
        const deadline=mcEl("div","row");
        deadline.append(mcEl("span","",mcTr("Ready By")+" · "+mcTime(a.ready_by,d.timezone)));
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"ready_by"))
          deadline.append(mcButton(mcTr("Set charging deadline"),()=>
            this.openNative("asset",a.id,"ready_by")));
        detail.append(deadline);
        if(this._scheduleEditor!==a.id)this.nativeRepeatEditor(detail,a);
        // Native upstream price/SoC policy remains Asset-owned and one
        // Config Entry preference; this view never stores price decisions.
        mcPair(detail,mcTr("Price currency"),
          a.price_currency||mcTr("Choose currency before price limits"));
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"price_currency")){
          const edit=mcButton(mcTr("Set price currency"),()=>
            this.openNative("asset",a.id,"price_currency"));
          edit.disabled=this._settingsBusy;
          detail.append(edit);
        }
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"earliest_start_at")){
          detail.append(mcButton(mcTr("Set earliest start"),()=>
            this.openNative("asset",a.id,"earliest_start_at")));
        }
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"opportunistic_kind")){
          const strategy=this.field(detail,mcTr("Opportunistic charging"),
            a.opportunistic_kind||"off",null,[
              ["off",mcTr("Off")],["type1",mcTr("Type 1 — cap fraction")],
              ["type2",mcTr("Type 2 — tomorrow price")],
            ]);
          strategy.disabled=this._settingsBusy;
          strategy.addEventListener("change",()=>
            void this.nativeSelect("asset",a.id,"opportunistic_kind",
                                   strategy.value));
        }
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"continuous_charging")){
          detail.append(mcEl("h4","",mcTr("Continuity and price strategy")));
          const continuity=this.field(
            detail,mcTr("Charging pattern"),
            a.continuous_charging?"continuous":"flexible",null,[
              ["flexible",mcTr("Flexible cheapest quarters")],
              ["continuous",mcTr("One continuous charge")],
            ]);
          continuity.disabled=this._settingsBusy;
          continuity.addEventListener("change",()=>
            void this.nativeSelect("asset",a.id,
                                  "continuous_charging",continuity.value));
        }
        if(this.canEditSettings())this.ownerColorControl(detail,"asset",a);
        for(const [field,label] of [
          ["kind","Asset type"],["expected_connection_at","Expected"],
          ["expires_at","Guest expiry"],["name","Asset name"]
        ]){
          if(!this.canEditSettings()||!this.ownerEntity("asset",a.id,field))continue;
          const row=mcEl("div","row");
          row.append(mcEl("span","muted small",label),mcButton("Edit",
            ()=>this.openNative("asset",a.id,field)));
          detail.append(row);
        }
        card.append(detail);
      }
      container.append(card);
    }
    if(this.canEditSettings()&&this._assetEditor==="new"){
      const form=mcEl("form","card");form.append(mcEl("h3","","Add a chargeable asset"));
      const name=this.field(form,"Asset name","","text");
      const kind=this.field(form,"Asset type","car",null,[
        ["car",mcTr("Car")],["bicycle",mcTr("Bicycle")],
        ["motorcycle",mcTr("Motorcycle")],["scooter",mcTr("Scooter")],
        ["other",mcTr("Other")]
      ]);
      const goal=this.field(form,mcTr("Charging goal"),"energy",null,[
        ["energy",mcTr("Energy (kWh)")],["duration",mcTr("Duration (minutes)")],
        ["budget",mcTr("Budget (€)")],["none",mcTr("Set later")]
      ]);
      const amount=this.field(form,mcTr("Charging amount"),"","number");
      const free=(d.configuration.chargers||[]).filter(ch=>!ch.asset);
      const assigned=this.field(form,mcTr("Select free charger (optional)"),
        "none",null,[["none",mcTr("Assign later")],
                    ...free.map(ch=>[ch.id,ch.name])]);
      const temporary=this.field(form,"Temporary guest","yes",null,
        [["yes","Yes — temporary guest"],["no","No — permanent asset"]]);
      const expiry=this.field(form,mcTr("Guest for"),"24",null,[
        ["4",mcTr("4 hours")],["24",mcTr("24 hours")],
        ["48",mcTr("48 hours")],["168",mcTr("7 days")]
      ]);
      form.append(mcButton("Create asset",()=>{
        const id=name.value.trim().toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"");
        const changes={name:name.value.trim(),kind:kind.value};
        if(assigned.value!=="none")
          changes.assign_charger_id=assigned.value;
        const requested=amount.value.trim();
        if(goal.value!=="none"&&requested){
          const value=Number(requested);
          if(!Number.isFinite(value)||value<=0||
              goal.value==="duration"&&!Number.isInteger(value)){
            this._settingsFeedback={status:"rejected",message:"Invalid charging amount"};
            this.render();return;
          }
          if(goal.value==="energy")changes.requested_kwh=value;
          if(goal.value==="duration")changes.requested_duration_minutes=value;
          if(goal.value==="budget"){
            changes.requested_budget_amount=value;
            changes.requested_budget_currency="EUR";
          }
        }
        if(temporary.value==="yes"){
          changes.temporary=true;
          // Relative expiry is a real absolute UTC instant; browser local
          // timezone cannot silently reinterpret a household wall clock.
          changes.expires_at=new Date(Date.now()+Number(expiry.value)*3600000).toISOString();
        }
        this.saveSettings("asset",id,changes,"create");
      }));
      container.append(form);
    }
    this.feedback(container);
    if(this.canEditSettings())container.append(mcButton(this._assetEditor==="new"?"Cancel adding":"Add asset",()=>{
      this._assetEditor=this._assetEditor==="new"?"":"new";this.render();
    }));
  }
  chargers(container){
    const d=this._data,chargers=d.configuration.chargers||[],observations=(d.observations||{}).chargers||{};
    this.title(container,mcTr("Chargers")+" ("+chargers.length+")");
    this.feedback(container);
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
      if(this.canManage()&&obs.connected?.quality==="ok"&&obs.connected.value===true&&
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
        if(latest.cost===null && latest.estimated_variable_cost!==undefined){
          mcPair(card,mcTr("Indicative variable energy cost"),
            latest.estimated_variable_cost+" "+
            latest.estimated_variable_cost_currency);
          card.append(mcEl("p","muted small",
            mcTr("Power-derived estimate, not a bill")));
        }
      }
      if(this._open===c.id){
        const detail=mcEl("div","details");
        mcPair(detail,"Rated power",c.rated_power_kw+" kW");
        mcPair(detail,"Phases",c.phase_count||"Unverified");
        mcPair(detail,"Current range",c.min_current_a&&c.max_current_a?c.min_current_a+"–"+c.max_current_a+" A":"Unknown");
        if(c.kind==="variable_current"){
          for(const [field,label] of [
            ["min_charging_power_kw","Minimum charging power"],
            ["max_charging_power_kw","Maximum charging power"],
            ["set_charging_power_kw","Set charging power"]
          ]){
            const session=(d.active_sessions||{})[c.id];
            const kw=field==="set_charging_power_kw"?
              (session?.target_current_a!=null&&c.voltage_v&&c.phase_ids?.length?
                session.target_current_a*c.voltage_v*c.phase_ids.length/1000:null):
              c[field];
            mcPair(detail,mcTr(label),kw==null?mcTr("Not set"):Number(kw).toFixed(2)+" kW");
            this.nativeNumberEditor(detail,"charger",c.id,field,label,
              kw,"kW");
          }
        }else{
          mcPair(detail,mcTr("Charging power control"),mcTr("On/off only"));
        }
        mcPair(detail,"Source state",obs.power_kw?mcTr(obs.power_kw.quality==="ok"?"Ready":"Unavailable"):"Unknown");
        const actual=(d.command_outcomes||{})[c.id]||{};
        mcPair(detail,"Status",mcTr(actual.status==="confirmed"?"Confirmed":actual.status==="rejected"?"Rejected":actual.status==="execution_unknown"?"Unavailable":"No action"));
        if(actual.reason)mcPair(detail,"Reason",mcReason(actual.reason));
        if(actual.readback_at)mcPair(detail,"Measured confirmation",mcTime(actual.readback_at,d.timezone));
        if(this.canEditSettings())this.ownerColorControl(detail,"charger",c);
        if(this.canEditSettings()&&this.ownerEntity("charger",c.id,"asset")){
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
      if(this.canManage()&&capability.start_allowed){
        const start=mcButton("Start charging",()=>this.command(c.id,"start"));
        start.disabled=this._commandBusy;
        controls.append(start);
      }
      if(this.canManage()&&capability.stop_allowed){
        const stop=mcButton("Stop charging",()=>this.command(c.id,"stop"));
        stop.disabled=this._commandBusy;
        controls.append(stop);
      }
      if(this.canManage()&&capability.pause_allowed){
        const pause=mcButton(mcTr("Pause charging"),()=>this.command(c.id,"pause"));
        pause.disabled=this._commandBusy;
        controls.append(pause);
      }
      if(this.canManage()&&capability.resume_allowed){
        const resume=mcButton(mcTr("Resume charging"),()=>this.command(c.id,"resume"));
        resume.disabled=this._commandBusy;
        controls.append(resume);
      }
      if(controls.children.length)card.append(controls);
      if(this.canManage()&&!c.asset){
        // Always allow preparing a finite manual request. The backend is
        // authoritative for native source/safety/physical permission.
        const oneOff=mcEl("section","card");
        oneOff.append(mcEl("h3","",mcTr("Manual one-off charge")));
        const draft=this._manualDrafts[c.id]||{energy:"",minutes:"",budget:""};
        this._manualDrafts[c.id]=draft;
        const energy=this.field(oneOff,mcTr("Energy limit (kWh)"),draft.energy,"number");
        const minutes=this.field(oneOff,mcTr("Time limit (minutes)"),draft.minutes,"number");
        const budget=this.field(oneOff,mcTr("Budget limit (€)"),draft.budget,"number");
        energy.addEventListener("input",()=>{draft.energy=energy.value;});
        minutes.addEventListener("input",()=>{draft.minutes=minutes.value;});
        budget.addEventListener("input",()=>{draft.budget=budget.value;});
        const submit=mcButton(mcTr("Start bounded session"),()=>{
          const amount=energy.value.trim(),time=minutes.value.trim(),
                money=budget.value.trim();
          draft.energy=amount;draft.minutes=time;draft.budget=money;
          if([amount,time,money].filter(Boolean).length!==1||
              [amount,time,money].filter(Boolean).some(x=>
                !Number.isFinite(Number(x))||Number(x)<=0)||
              (time&&!Number.isInteger(Number(time)))){
            this._commandFeedback[c.id]={
              status:"rejected",reason:"ONE_FINITE_MANUAL_LIMIT_REQUIRED"
            };
            this.render();return;
          }
          this.command(c.id,"start",amount?{energy_kwh:Number(amount)}:
            time?{duration_minutes:Number(time)}:
            {cost_amount:Number(money),currency:"EUR"});
        });
        submit.disabled=this._commandBusy||!capability.manual_one_off_allowed;
        oneOff.append(submit);
        if(!capability.manual_one_off_allowed)
          oneOff.append(mcEl("p","muted small",
            mcTr("Start unavailable")+" · "+
            mcReason(capability.manual_one_off_reason||"SOURCE_NOT_SELECTED")));
        card.append(oneOff);
      }
      if(!capability.start_allowed && capability.reason && c.asset)
        card.append(mcEl("p","muted small",mcTr("Unavailable")+" · "+mcReason(capability.reason)));
      if(outcome){
        const bad=outcome.status==="rejected"||outcome.status==="execution_unknown";
        const label=bad?mcReason(outcome.reason):outcome.status==="confirmed"?
          (outcome.action==="stop"?"Stopped":
           outcome.action==="pause"?mcTr("Paused"):
           outcome.action==="resume"?mcTr("Ready for next plan"):"Charging"):"Pending";
        const status=mcEl("p","small"+(bad?" error":""),label);
        status.setAttribute("role",bad?"alert":"status");
        card.append(status);
      }
      container.append(card);
    }
    if(this.canEditSettings()){
      const add=mcEl("a","action",mcTr("Add charger"));
      add.href="/config/integrations/integration/robotix_multicharge";
      add.setAttribute("aria-label",mcTr("Add charger"));
      container.append(add);
    }
  }
  settings(container){
    const d=this._data,c=d.configuration||{},ctl=c.controller||{};
    this.title(container,"Settings");
    if(d.configuration_managed_by_yaml)mcPair(
      container,"Configuration",
      d.configuration_managed_by_json?
        "JSON · read-only; edit your MultiCharge JSON and restart":
        "YAML · read-only; edit Home Assistant YAML and restart"
    );

    const toolbar=mcEl("div","settings-toolbar");
    this.configure(toolbar);
    if(this.canEditSettings()){
      const edit=mcButton(this._yamlFlow?"Cancel YAML":"Edit YAML",()=>
        this._yamlFlow?this.cancelYamlEditor():this.openYamlEditor());
      edit.disabled=this._yamlBusy;
      toolbar.append(edit);
    }
    container.append(toolbar);
    this.feedback(container);
    if(this._yamlError&&!this._yamlFlow){
      const warning=mcEl("p","yaml-error",this._yamlError);
      warning.setAttribute("role","alert");container.append(warning);
    }
    this.yamlEditor(container);
    const settingsGrid=mcEl("div","settings-grid");
    for(const title of MC_SETTINGS){
      const open=title===this._settingsOpen;
      const group=mcEl("section","card settings-card"+(open?" expanded":""));
      const heading=mcEl("div","settings-heading");
      heading.append(mcEl("h3","",title));
      const summary=title==="Charging site"?ctl.name||"Not set":
        title==="Sources & bindings"?[ctl.price_entity||ctl.current_price_entity?"Tariff":null,
          ctl.solar_entity||ctl.solar_power_entity||ctl.solar_surplus_entity?"Solar":null,
          ctl.home_power_entity?"Home":null,
          ctl.grid_power_entity?"Grid":null,
          ctl.binding_entity?"Capacity":null].filter(Boolean).join(" · ")||"No source":
        title==="Charging strategy"?ctl.mode||"Off":
        title==="Safety & limits"?(ctl.max_power_kw===undefined?"No capacity":ctl.max_power_kw+" kW")+" · "+(ctl.max_parallel||1)+" parallel":
        title==="Integrations"?(c.chargers||[]).length+" chargers":
        d.configuration_managed_by_yaml?"YAML / JSON source · read-only":"Expert YAML / JSON configuration";
      heading.append(mcEl("p","muted small",summary));
      const row=mcEl("div","row");
      row.append(heading,mcButton(open?"Close":"Details",()=>{
        this._settingsOpen=open?"":title;this.render();
      }));
      group.append(row);
      if(open){
        const detail=mcEl("div","details");
        if(title==="Charging site"){
          mcPair(detail,"Site name",ctl.name);
          if(this.canEditSettings()&&this.ownerEntity("controller",ctl.id,"name")){
            const rename=mcEl("div","row");
            rename.append(mcEl("span","",mcTr("Site name")),
              mcButton("Edit",()=>this.openNative("controller",ctl.id,"name")));
            detail.append(rename);
          }
          this.nativeNumberEditor(detail,"controller",ctl.id,"max_parallel",
            "Parallel chargers",ctl.max_parallel);
          this.nativeNumberEditor(detail,"controller",ctl.id,"max_power_kw",
            "Maximum group power",ctl.max_power_kw,"kW");
        }else if(title==="Charging strategy"){
          const options=mcEl("div","chips");
          for(const mode of this.canEditSettings()?MC_MODES:[]){
            const btn=mcButton(mode,()=>this.nativeSelect("controller",ctl.id,"mode",mode));
            btn.disabled=this._settingsBusy||mode===ctl.mode||
              !this.ownerEntity("controller",ctl.id,"mode");
            if(mode===ctl.mode)btn.className="active";
            options.append(btn);
          }
          detail.append(options);
          if(!this.canEditSettings())mcPair(detail,"Charging mode",ctl.mode||"Unknown");
        }else if(title==="Sources & bindings"){
          for(const [field,label] of [
            ["solar_power_entity","Solar production"],
            ["home_power_entity","Home consumption"],
            ["grid_power_entity","Grid power"],
            ["solar_surplus_entity","Solar surplus"],
            ["price_entity","Future tariff intervals"],
            ["current_price_entity","Current import price"],
            ["export_price_entity","Current export price"],
            ["solar_entity","Solar intervals"],
            ["site_power_entity","Site power"],["binding_entity","Capacity"]
          ]){
            mcPair(detail,label,ctl[field]||mcTr("Not set"));
            if(this.canEditSettings()&&this.ownerEntity("controller",ctl.id,field)){
              const sourceEdit=mcEl("div","row");
              sourceEdit.append(mcEl("span","muted small",mcTr(label)+" "+mcTr("source")),
                mcButton(mcTr("Edit"),()=>this.openNative("controller",ctl.id,field)));
              detail.append(sourceEdit);
            }
          }
        }else if(title==="Integrations"){
          mcPair(detail,"Tariff",mcReason((d.observations||{}).sources?.tariff_quality));
          mcPair(detail,"Solar",mcReason((d.observations||{}).sources?.solar_quality));
          mcPair(detail,"Capacity",mcReason((d.observations||{}).sources?.binding_quality));
          for(const [field,label,unit] of [
            ["solar_power","Solar production","kW"],
            ["home_power","Home consumption","kW"],
            ["grid_power","Grid power","kW"],
            ["available_solar_kw","Available surplus","kW"],
            ["current_export_price","Current export price",""]
          ]){
            const reading=(d.observations||{}).sources?.[field];
            mcPair(detail,label,reading?.quality==="ok"||reading?.quality==="OK"?
              String(reading.value)+(unit?" "+unit:"") : mcTr("Unknown"));
          }
          mcPair(detail,"Solar source",ctl.solar_source_kind||"none");
          mcPair(detail,"Grid direction",ctl.grid_power_direction||"import_positive");
        }else if(title==="Safety & limits"){
          mcPair(detail,"Maximum group kW",ctl.max_power_kw===undefined?
            "Unknown":ctl.max_power_kw+" kW");
          this.nativeNumberEditor(detail,"controller",ctl.id,"max_power_kw",
            "Maximum group power",ctl.max_power_kw,"kW");
          this.nativeNumberEditor(detail,"controller",ctl.id,"max_parallel",
            "Parallel chargers",ctl.max_parallel);
          const phases=Object.entries(ctl.phase_limits_a||{});
          mcPair(detail,"Electrical limits",
            phases.length?phases.map(([id,amps])=>id+": "+amps+" A").join(" · "):mcTr("Not set"));
        }else{
          mcPair(detail,"Configuration",d.configuration_managed_by_yaml?
            (d.configuration_managed_by_json?"JSON source":"YAML source"):"Home Assistant settings");
          detail.append(mcEl("p","muted small",
            d.configuration_managed_by_yaml?
              "This site is managed by external Home Assistant YAML/JSON. Edit its existing source file, validate and restart. The dashboard will not overwrite that authority.":
              "For GUI-managed sites, use Edit YAML above, review changes and save through Home Assistant. The Config Entry remains the only authority; no separate file or charging writer is created."));
          if(!d.configuration_managed_by_yaml)detail.append(mcEl(
            "p","muted small",
            "Select native Home Assistant sources through Configure → Energy & prices; "+
            "Home Assistant Energy Dashboard sources may be reused. No template sensors "+
            "or packages are required for MultiCharge configuration."));
        }
        group.append(detail);
      }
      settingsGrid.append(group);
    }
    container.append(settingsGrid);
  }
}
if(!customElements.get("robotix-multicharge-card"))customElements.define("robotix-multicharge-card",RobotixMultiChargeCard);

/* Native HA sidebar view: reuse the one source-backed card and its five tabs.
 * No second state store, permissions model, or physical command channel.
 */
class RobotixMultiChargePanel extends HTMLElement {
  constructor(){
    super();
    this.attachShadow({mode:"open"});
    const style=document.createElement("style");
    style.textContent=`
      :host { display:block; min-height:100%; box-sizing:border-box; }
      .panel { max-width:1440px; margin:0 auto; padding:16px;
               box-sizing:border-box; }
      robotix-multicharge-card { display:block; width:100%; }
      @media (max-width:600px) { .panel { padding:8px; } }
    `;
    this._content=document.createElement("main");
    this._content.className="panel";
    this._card=document.createElement("robotix-multicharge-card");
    this._card.setConfig({});
    this._content.append(this._card);
    this.shadowRoot.append(style,this._content);
  }
  set hass(value){
    this._hass=value;
    this._card.hass=value;
  }
  get hass(){return this._hass;}
  set panel(value){this._panel=value;}
  get panel(){return this._panel;}
  set narrow(value){this._narrow=value;}
  get narrow(){return this._narrow;}
  disconnectedCallback(){
    if(typeof this._card.disconnectedCallback==="function"){
      this._card.disconnectedCallback();
    }
  }
}
if(!customElements.get("robotix-multicharge-panel")){
  customElements.define("robotix-multicharge-panel",RobotixMultiChargePanel);
}

window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==="robotix-multicharge-card")){
  window.customCards.push({type:"robotix-multicharge-card",name:"Robotix MultiCharge",description:"Charging plan"});
}