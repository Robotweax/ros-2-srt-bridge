# Handoff: ROS-2-Brücke für Robotweax CONTROL/SENSOR

Datum: 2026-11-04 · Einstieg für einen Entwickler

## Auftrag und aktueller Zustand

Implementiere die in [ARCHITECTURE.md](ARCHITECTURE.md) beschriebene selektive
ROS-2-Brücke. Beginne mit M0 und arbeite bis zum simulierten ROS-Demonstrator M2;
danach folgen Netzwerkvergleich M3 und der Intrinsic-Adapter M4.

**Bei der ursprünglichen Übergabe waren ausschließlich diese beiden Planungsdokumente vorhanden.** Es wurden
keine Bridge-Pakete, Container, ROS-Launchfiles oder Intrinsic-Adapter erstellt.
Es wurden keine Builds, Netzwerkversuche oder Robotertests für dieses Vorhaben
ausgeführt. Die Architektur ist kein gemessener Leistungs- oder Sicherheitsnachweis.

Die Grundentscheidung ist getroffen: SENSOR für kleine aktuelle Zustände,
CONTROL für einzelne bestätigte Aufträge, zwei getrennte SRT-Verbindungen,
begrenzte Queues und ein dauerhaftes Auftragsjournal. Der erste Handler ändert
die Messrate eines Simulators. Eine weitere reine Videobrücke ist nicht das Ziel.

## 1. Vor Arbeitsbeginn lesen

1. Anwendbare lokale `AGENTS.md` und die vollständige [Architektur](ARCHITECTURE.md).
2. CONTROL-, SENSOR- und SESSIONAUTH-Verträge am unten genannten SRT-Pin.
3. Installierter öffentlicher C-API-Consumer und Testanleitung am selben Pin.
4. Vor M4 Intrinsic-README und ICON-/ROS-2-Tutorial an dessen eigenem Pin.

Dieser Ordner liegt als neues Teilprojekt im vorhandenen SRT-Checkout. Die
`HANDOFF.md` im Repository-Wurzelverzeichnis gehört zu einer anderen Aufgabe.
Vorhandene Änderungen, andere Teilprojekte und deren Übergaben erhalten.
Für die Implementierung kann dieser Ordner in ein eigenständiges Repository
übernommen werden; SRT bleibt eine installierte Abhängigkeit. Vor neuen Dateien
den tatsächlichen Arbeitsbaum prüfen. Keine vorhandenen Änderungen zurücksetzen.

## 2. Pins und Umgebung

| Zweck | Referenz |
| --- | --- |
| Lokaler Ausgangscheckout, nur Quellenkontext | SRT `09ceab33e1fc190472558fdb4d873f38b76fa320`, Version 0.2.8 |
| Zu qualifizierender SRT-Kandidat | `52be7c86ee1f303cbb0c8718c364217e4dd97a36`, CMake-Version 0.3.1 |
| Zu qualifizierender Intrinsic-Pin für M4 | `723c3ee01f155f7a8bb04e449d917fe8ac5784e9` |
| MVP-Betriebssystem | Ubuntu 24.04, Linux amd64 |
| MVP-ROS | Jazzy; beide Enden identische Typ-Paketversionen |
| Sprache / Crypto | C++20 / OpenSSL 3.x, GCM und SESSIONAUTH v2 |

Die neuere Quelle wird in einem separaten Dependency-Checkout bereitgestellt.
Nicht den bestehenden, anderweitig genutzten SRT-Arbeitsbaum auf den Pin resetten.
Ein geeigneter vorhandener Checkout kann wiederverwendet werden. Gleiche
Versionsnummern allein genügen nicht: Headers, Bibliothek, Flags und SHA müssen
zusammenpassen. Für den MVP kein `latest`-Container und kein ungeprüftes `main`.

In M0 `baselines/dependencies.json` anlegen: SRT-/Intrinsic-SHA, Container-Digest,
ROS-Pakete, RMW, Protobuf, SQLite, Compiler, OpenSSL, Architektur und Buildflags.
Intrinsic verlangt laut gelesenem README Lyrical; dessen Integration separat
bauen. Die Jazzy-Baseline ist keine Behauptung einer Intrinsic-Kompatibilität.

## 3. Erster ausführbarer Schritt: SRT-Consumer qualifizieren

In einem vorbereiteten Linux-Entwicklungscontainer sind CMake, C++20-Compiler,
OpenSSL-Entwicklungsdateien und Python erforderlich. ROS ist für die erste
Consumer-Prüfung noch nicht erforderlich. Die folgenden Befehle gelten für den
separaten **gepinnten SRT-Quellbaum**, nicht für diesen Dokumentationsordner.
Sie sind ein Startrezept und wurden im Rahmen dieser Übergabe nicht ausgeführt.

```sh
set -eu
# Im Dependency-Checkout; bei einem anderen HEAD zuerst dessen Herkunft klären.
test "$(git rev-parse HEAD)" = 52be7c86ee1f303cbb0c8718c364217e4dd97a36
git status --short

cmake -S . -B build-ros2-profile \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/stage-ros2-profile" \
  -DROBOTWEAX_SRT_INSTALL_LAYOUT=namespaced \
  -DROBOTWEAX_SRT_BUILD_TESTS=ON \
  -DROBOTWEAX_SRT_BUILD_EXAMPLES=ON \
  -DROBOTWEAX_SRT_BUILD_BENCHMARKS=OFF \
  -DROBOTWEAX_SRT_BUILD_TOOLS=OFF \
  -DROBOTWEAX_SRT_CRYPTO_BACKEND=openssl \
  -DENABLE_AEAD_API_PREVIEW=ON \
  -DROBOTWEAX_SRT_ENABLE_EXPERIMENTAL_ACP1=OFF
cmake --build build-ros2-profile --parallel 2
ctest --test-dir build-ros2-profile -N
ctest --test-dir build-ros2-profile -L profile --output-on-failure
cmake --install build-ros2-profile
```

Vor dem gefilterten Lauf die tatsächliche Testinventur prüfen. Null ausgewählte
Tests sind ein Fehler. Das `profile`-Label ist ein Einstieg, kein vollständiger
SESSIONAUTH-/Reconnect-Nachweis. Ergänze die am Pin dokumentierten relevanten
Tests und protokolliere Namen, Zahl, Ergebnisse und ausgelassene Umgebungsfälle.
Eine verschmutzte Dependency-Quelle muss im Manifest sichtbar sein und ist
keine unveränderte Pin-Qualifikation.

Ein eigener kleiner installierter Consumer muss danach über die öffentliche
C-API zwei echte Sockets betreiben und für CONTROL **und** SENSOR prüfen:

- Explizites Profil, AES-GCM und SESSIONAUTH v2; kein optionales Downgrade.
- Payload 1.024 Byte bei IPv4/MSS 1500 und IPv6/MSS 1280, identische Einstellungen
  auf beiden Seiten; CONTROL zusätzlich bis zur 4.096-Byte-Bridge-Grenze.
- Falsches Profil, falsches Secret, fehlendes GCM und fehlende SESSIONAUTH ablehnen.
- Gültige Samples empfangen, große SENSOR-Nachricht ablehnen, epoll/Timeout und
  begrenztes Close korrekt behandeln.

Die vorhandenen Message-Demos sind hilfreich, ersetzen aber nicht diesen
Consumer mit der vollständigen gewählten Optionskombination. Linker-Anbindung:

```cmake
find_package(RobotweaxSRT CONFIG REQUIRED)
target_compile_features(profile_probe PRIVATE cxx_std_20)
target_link_libraries(profile_probe PRIVATE RobotweaxSRT::srt)
```

`profile_probe` ist ein in M0 anzulegender Target. Das explizite Versions-/SHA-
Gate erfolgt über den Dependency-Lock und das Buildmanifest; keine pauschale
0.2-ABI-Anforderung für eine 0.3-Bibliothek setzen. Keine privaten C++-Headers.

## 4. Geplante Projektstruktur

Diese Struktur anlegen; sie existiert zum Übergabezeitpunkt noch nicht:

```text
SRT-ROS2/
  ARCHITECTURE.md
  HANDOFF.md
  baselines/dependencies.json
  config/robot.yaml
  config/operator.yaml
  src/robotweax_srt_bridge_core/
  src/robotweax_srt_bridge_msgs/
  src/robotweax_srt_bridge/
  src/robotweax_srt_bridge_demo/
  tests/protocol/
  tests/integration/
  tests/network/
  tools/
  evidence/                  # nur bereinigte, bewusst veröffentlichbare Resultate
```

Build-/Install-/Logverzeichnisse, Credentials und rohe Laufartefakte lokal
ignorieren. Der Core muss auch ohne ROS mit CMake testbar sein. Für ROS
`ament_cmake`/colcon verwenden. Ein README mit tatsächlich funktionierenden
Build-/Startbefehlen entsteht mit M2, nicht mit erfundenen heutigen Launchnamen.

## 5. Implementierung in kleinen überprüfbaren Schritten

### M0 — Umgebung und Profilkombination

- Dependency-Lock und Container-Basis festhalten.
- Obigen Consumer und Negative Cases ausführen; tatsächliche Grenzen erfassen.
- ROS-Typhash-/CDR-Verfügbarkeit und Worst-Case-Größen beider MVP-Nachrichten
  prüfen. 96-Byte-Envelope plus CDR muss in 1.024 Byte passen.
- Abweichungen zuerst im Architekturvertrag klären; keine stillen Fallbacks.

### M1 — Core ohne ROS

- 96-Byte-Envelope, Management-Protobufs und kanonischen Routenmanifest mit
  Golden-Vektoren implementieren. Unbekannte Versionen/Flags/Routen ablehnen.
- CONTROL-Handshake, SENSOR-Binding, ClockMapper und Lifecycle bauen.
- SENSOR latest-only Queue, Sequenz-/Epochprüfung und Altersprüfung umsetzen.
- SQLite-Journal mit Admission-, Dispatch-, Ergebnis- und UNKNOWN-Semantik bauen.
- Abbruch nach Journal-Commit und vor/nach Handler-Aufruf gezielt injizieren.
  Erneuter Send desselben Auftrags darf nicht blind erneut ausführen.
- Getrennte Queues und gemeinsame Bandbreiten-Admission implementieren.

### M2 — ROS-Demonstrator

- Zwei Nodes in isolierten ROS-Domänen verbinden. Bridge-Core separat zum
  ROS-Executor betreiben; keine blockierenden SRT-Aufrufe in ROS-Callbacks.
- Imu und JointState typisiert mit Größen-/Schema-/QoS-Gates übertragen.
- ExecuteCommand/GetCommandStatus und den simulierten SetMeasurementRate-Handler
  anschließen. ID, Generation und Ergebnis an einem realen Zustandswechsel prüfen.
- Eine saubere Demo zeigt: aktuelle Samples, Messratenwechsel, bestätigtes
  Ergebnis, 2-s-Unterbrechung, Wiederanlauf ohne alte Samples oder doppelte Wirkung.
- Tatsächliche ROS-Build-, Launch- und Testbefehle dokumentieren. Ein Transport-
  ACK oder ein einzelner erfolgreicher Send genügt nicht als Abnahme.

### M3 — Netzqualifikation und Vergleich

- N0–N5 aus der Architektur ausführen, Erstfehler und Seeds bewahren.
- Direkten DDS-Verkehr zwischen den Enden ausschließen; einen separaten,
  vergleichbar konfigurierten DDS-Baseline-Lauf ermöglichen.
- Ergebnisse auf Anwendungsebene messen, mit Raten, Altersabdeckung, CPU/RSS,
  Overhead, CONTROL-Ergebniszeiten und Reconnect. Kein pauschales „schneller“
  ohne die zugrunde liegenden Bedingungen und Daten.

### M4 — Intrinsic

- Tatsächliche Lyrical-/Runtime-Pins und erlaubte Zustands-/Auftrags-APIs erfassen.
- Core erneut gegen die passende Toolchain bauen, beide Gegenstellen kompatibel.
- Zuerst Zustandsbeobachtung, dann einen simulierten Diagnoseauftrag integrieren.
- Auftrags-ID/-Status-Abbildung und Unsicherheitsfälle dokumentieren. ICON/HAL-
  Shared Memory und Echtzeitthreads bleiben außerhalb des Netzwerkadapters.

## 6. Tests, die nicht fehlen dürfen

| Fall | Erwartung |
| --- | --- |
| Gleiche Request-ID, anderer Payload | `CONFLICT`, kein Handler-Aufruf. |
| Reconnect nach Ergebnis-Commit vor Zustellung | QUERY liefert ursprüngliches Ergebnis, keine neue Ausführung. |
| Absturz nach Dispatch vor Ergebnis-Commit | `UNKNOWN`, kein automatischer Retry. |
| Neustart mit angenommenem, noch nicht dispatchtem Auftrag | `REJECTED/CONTEXT_LOST`, keine späte Ausführung aus altem Kontext. |
| Frist läuft in Queue ab | `EXPIRED` vor Dispatch. |
| Unbekannte Clock-Abbildung / Sprung / Neustart | Kein frischer Sample oder Auftrag vor erfolgreicher Neuqualifikation. |
| Alter Sample nach neuerem Sample durch FEC | Gezählt und verworfen; publizierte Sequenz steigt streng. |
| SENSOR-Übergröße / Typhash-Mismatch | Expliziter Fehler; kein Abschneiden oder Profilwechsel. |
| Volle Queues / volles Journal / langsamer Peer | Begrenzter Speicher, beobachtbares BUSY bzw. SENSOR-Ersetzung. |
| Datenträger voll / Fehler beim Ergebnis-Commit | Kein unbelegtes SUCCEEDED; ursprüngliche ID bleibt rekonstruierbar bzw. UNKNOWN. |
| CONTROL gestört, SENSOR noch erreichbar | Alte Sitzung invalidieren; keine unkontrollierte Weiterpublikation. |
| Shutdown während Reconnect oder vollem Sendpuffer | Höchstens fünf Sekunden im Lifecycle-Test, kein 180-s-Linger, keine Callback-Nutzung freigegebenen Speichers. |

M0 qualifiziert zusätzlich die genaue Transport-/Crypto-Kombination; M1 testet
Wire und Zustandsautomaten deterministisch. M2 verwendet echte SRT-Sockets und
ROS-Nodes. M3 verwendet reale Kernel-Netzbeeinträchtigung in isolierter Umgebung.
Mocks oder Loopback erfüllen die jeweils nachfolgenden Stufen nicht.

## 7. Nächste Übergabe und Definition of Done

### Ursprünglicher Übernahmestand 2026-11-04

- Repository für M0–M3: https://github.com/Robotweax/ros-2-srt-bridge.
- Separates Repository für den späteren M4-Adapter:
  https://github.com/Robotweax/intrinsic-core-srt-integration.
- Beide GitHub-Repositories waren erreichbar und ohne Branches. Lokales
  Bootstrap in diesem Ordner; kein Commit oder Push bei der Übernahme.
- Architektur und Handoff vollständig gelesen. README, lokale Ignore-Regeln
  und `baselines/dependencies.json` als **unqualifiziertes Kandidatenmanifest**
  ergänzt. Unbekannte Digests/Versionen bleiben ausdrücklich `null`.
- Host: Darwin arm64. `docker version --format '{{json .Server}}'` scheiterte
  im Kontext `desktop-linux`: Docker-Socket fehlt, kein Server verfügbar.
  Docker Desktop ist installiert. Kein Linux-Build und keine Profilprobe gestartet.
- M0 ist offen. Nächster Ausführungsschritt: Linux-amd64-Umgebung bereitstellen,
  Image-Digest pinnen und separaten SRT-Kandidaten qualifizieren. Erst danach M1.
- Intrinsic bleibt M4 im eigenen Repository. Bestehender übergeordneter
  SRT-Arbeitsbaum und dessen Änderungen bleiben erhalten.

### Verifizierte Übernahme 2026-11-04

- Tatsächlich vorhanden waren nur Architektur, Handoff und README; die zuvor
  erwähnten lokalen Git-/Ignore-/Baseline-Dateien fehlten. Jetzt eigenständiges
  Repository mit Branch `main` und dem Bridge-Remote eingerichtet; kein Commit/Push.
- Kandidatenmanifest und Ignore-Regeln ergänzt. Beide Zielrepositories erneut
  erreichbar; Intrinsic bleibt M4.
- Docker-Daemon jetzt verfügbar. Ubuntu 24.04 Linux amd64 im isolierten Container
  erfolgreich unter Emulation gestartet. Image-Referenz und lokale Plattform-ID
  im Kandidatenmanifest erfasst; noch kein qualifiziertes Entwicklungsimage.
- Übergeordneter SRT-HEAD bei Prüfung: `49e615aa6996e2c5a366a426d09bfe3ca2d24c2c`.
  Keine Änderung am bestehenden SRT-Arbeitsbaum.
- M0 weiterhin offen: separaten Pin-Checkout und Entwicklungsimage bereitstellen,
  Verträge am Pin lesen, SRT bauen/installieren und kombinierte Profilprobe erstellen.
- Befehle und tatsächliche Ergebnisse: [Übernahme-Evidenz](evidence/2026-11-04-takeover.md).

### Entwicklung M0 und erster M1-Baustein — 2026-11-04

- M0 lokal bestanden: sauberer SRT-Pin separat unter `.deps/srt`, namespaced
  installiertes statisches Paket, OpenSSL/GCM/SESSIONAUTH v2, experimentelle
  ACP1-/Controller-/Filteroptionen aus. Reale Linux-amd64-Sockets unter Emulation.
- `python3 tools/run_m0.py --build-image --srt-source ..` erstellt die Umgebung,
  validiert den Pin und hält pro Versuch Logs, Inventur, Paketstände und JUnit fest.
  Voraussetzung: das im README gepinnte ROS-Image zuvor herunterladen.
- Eigene öffentliche C-API-Probe: 40/40 Fälle bestanden (IPv4/MSS 1500,
  IPv6/MSS 1280, beide Profile, GCM+SESSIONAUTH, negative Gegenstellen,
  Größen-/TTL-Grenzen, epoll und Close bei gefülltem Sendpuffer).
- Upstream: vier GCM-Profilpartitionen, eine SESSIONAUTH-Admission-Partition und
  15 fokussierte SESSIONAUTH-Fälle bestanden. Nicht die gesamte Upstream-Suite.
- Jazzy-Typhash und CDR-Roundtrip geprüft: Imu 380 Byte; JointState mit sechs
  Gelenken, 64-Byte-Namen und vollständigen numerischen Arrays 684 Byte.
  `frame_id` jeweils 64 Byte. Beide passen mit 96-Byte-Envelope in 1.024 Byte.
- Kandidatenmanifest zur lokal qualifizierten M0-Baseline ergänzt. Image-Digests,
  tatsächliche Pakete, Archive-Hash und Buffer-Readbacks sind festgehalten.
- M1 begonnen: unabhängiger C++20-Wire-Codec, initiales Management-Protobuf-Schema,
  Golden-Vektor und 20.000 deterministische Mutationen (22.576 Assertions).
  GNU/Linux Debug, ASan+UBSan sowie eigenständiger macOS-arm64-Build bestanden.
- M1 ist **nicht fertig**: Management-Runtime-Validierung, kanonischer Routenhash,
  ClockMapper, Sessions/Binding/Reconnect, begrenzte Queues/Scheduler und
  SQLite-Journal fehlen. Noch keine ROS-Nodes oder Simulatorbefehle.
- Nachweise und Reproduktion: [M0/M1-Evidenz](evidence/m0-2026-11-04/README.md).
  Quelldateien sind noch uncommitted; kein Push, kein Intrinsic-Code.

### M1-Fortsetzung: Management und ClockMapper — 2026-11-04

- Management-Codec mit generiertem Protobuf und begrenzter Vorprüfung implementiert:
  maximal 512 Byte, bekannte/undoppelte Felder, Wire-Typen, feste Hash-/Epochlängen,
  UTF-8 ohne Steuerzeichen, Peer-ID bis 64 Byte und feste MVP-Limits.
- HELLO/WELCOME/READY/BIND/TIME_PROBE/TIME_REPLY werden typisiert validiert.
  Das ist noch keine Gegenstellenautorisierung oder Sitzung. COMMAND/STATUS/QUERY
  und ERROR-Payloads bleiben dem Journal-/Session-Baustein vorbehalten.
- ClockMapper implementiert asymmetrieunabhängige Offset-/Altersintervalle mit
  expliziten Drift-/Timestampfehlergrenzen, konservativer Rundung und Overflow-Gates.
  Unbekannte/zu breite/abgelaufene Modelle liefern keinen gültigen Alterswert.
  Epoch-/Domänenfehler, Rücksprung und Widerspruch sperren bis Reset.
- Protokollpräzisierung: Beide SRT-Endpunkte initiieren eigene Zeitprobes; t1/t4
  sind lokal, t2/t3 remote. Protobuf-Feldnummern unverändert, Rollenbezeichnungen
  auf Initiator/Responder korrigiert. Korrelation offener Probes ist noch anzuschließen.
- Deterministische Tests: 5.000 Drift-Szenarien mit Folgeproben und alten Ereignissen,
  Integergrenzen, Resets, Frischebudgets sowie 20.000 Management-Mutationen.
  Linux Debug und ASan+UBSan bestehen; Wire/Clock auch auf macOS arm64 geprüft.
- Reproduktion: `python3 tools/run_m1.py` mit dem M0-Image. Native Builds ohne
  Protobuf verwenden `-DBUILD_MANAGEMENT_CODEC=OFF`; der volle Core benötigt
  Protobuf ab 3.21. README und Architektur entsprechend aktualisiert.
- Nachweise: [M1-Evidenz](evidence/m1-clock-management-2026-11-04/README.md).
  M1 ist weiter offen: Routenmanifest/SHA, Session-/Probe-Korrelation, SRT-I/O,
  Reconnect, begrenzte Queues/Scheduler und SQLite-Journal. Kein Commit/Push.

### M1-Fortsetzung: Routenmanifest und Sitzungen — 2026-11-04

- Kanonischer RWRM-v1-Manifest mit SHA-256, sortierten IDs, Typ-/Hash-/QoS-/
  Richtungs-/Größen-/Budgetgrenzen und Enabled-Freigabe implementiert. Unabhängiger
  Python/struct/hashlib-Goldenvektor liegt unter `tests/protocol/routes-v1.*`.
- Session-Core implementiert HELLO/WELCOME, konfigurierte Peer-/Manifest-/Limit-
  Gates, gegenseitiges READY, beidseitig korrelierte Zeitprobes, SENSOR-Binding,
  Sequenz-/Epoch-/Domain-/Altersgates und Close-/Flush-Aktionen bei CONTROL-Verlust.
  Er besitzt noch keine eigenen Sockets oder Worker und ist nicht kopier-/bewegbar.
- Erforderliche Protokollpräzisierung: frische 16-Byte-Binding-ID je SENSOR-Socket,
  auf CONTROL exakt bestätigt. Feld 3 in BIND und READY; alte Prototypen ohne ID
  werden abgelehnt. Lokale Socketgenerationen schützen gegen alte Close-/Daten-
  Ereignisse. Source-Sequenzen laufen über Rebind und CONTROL-Reconnect weiter.
- Echte installierte SRT-Sockets testen IPv4 und IPv6, GCM+SESSIONAUTH v2,
  beidseitige READY-/Clock-Probes, verspätete alte Binding-Acks, SENSOR-Rebind,
  tatsächlichen CONTROL-Verlust, neuen Sitzungsaufbau und Abweisung alter Frames.
  Nutzdaten sind vier synthetische Byte, keine ROS-IMU und kein M2-Demonstrator.
- Kernverträge: fünf Tests in Debug und ASan+UBSan. Root-Regression: 47/47 Tests.
  Native Wire/Clock-Minimalspur erneut auf macOS arm64 geprüft.
- Reproduktion: `python3 tools/run_m1.py --native` nach M0; der Runner prüft den
  installierten SRT-Archive-Hash und führt die vollständige Root-Matrix aus.
- [Neue Evidenz](evidence/m1-sessions-2026-11-04/README.md) enthält Ergebnisse,
  Quellfingerprints, offene Grenzen und erhaltene Fehlläufe. Kein Commit/Push.
- M1 ist weiterhin offen: bounded Queues/Bandbreiten-Admission, Reconnectkampagne
  mit Jitter, Produktions-I/O-Owner und SQLite-Auftragsjournal/Crash-Semantik.

### M1-Fortsetzung: Queues, Bandbreite und Reconnectplan — 2026-11-04

- Feste CONTROL-Queue (64/256 KiB, COMMAND maximal 56/224 KiB), acht latest-only
  SENSOR-Slots und ein BIND-Retry-Slot implementiert. Eigene Packetkopien,
  BUSY/Drop-Zähler, Deadline-/Raten-/Sequenzgates, round-robin und Generationsgates.
- Session-Close/-Flush-Aktionen leeren die passenden Queues; wartende COMMAND-IDs
  werden für spätere Journalauflösung zurückgegeben. Kein ACCEPTED/Erfolg aus Queue-OK.
- Globales/SENSOR-Tokenbudget mit CONTROL-Reserve und einmaliger Reserve-/Commit-/
  Refund-Semantik implementiert. Overheadschätzer ist keine harte Wire-Garantie.
- Reconnectplan implementiert 250 ms–5 s mit geklemmtem ±20-%-Jitter, 3-s-Versuche,
  exakte 60-s-Kampagnen, eindeutige Versuche, Cancel, Deadlinegates und explizite
  Reaktivierung nach permanenten Fehlern. Keine blockierenden Sleeps im Plan.
- Native IPv4/IPv6-Harness nutzt Queues und Budget jetzt für Management/SENSOR,
  wendet Session-Invalidierungsaktionen an und verwirft absichtlich gealterte
  Samples vor SRT. Tatsächlich publizierte synthetische Sequenzen sind 1, 3, 4;
  die wartende 2 läuft lokal ab. Keine ROS-Nodes oder Auftragsausführung.
- Acht Kernverträge in Debug und ASan+UBSan bestanden, vollständige Root-Matrix
  50/50. Enthalten: 50.000 Queue-Ereignisse, zehn Sekunden synthetische Überlast,
  1.000 deterministische Reconnectkampagnen. Minimale native Host-Spur: vier Tests.
- Reproduktion bleibt `python3 tools/run_m1.py --native` nach M0.
  [Neue Evidenz](evidence/m1-queues-reconnect-2026-11-04/README.md) bewahrt Logs,
  Quellhashes, Ergebnisse und Fehlläufe. Kein Commit/Push.
- Noch offen: produktiver Socket-/epoll-Owner, bounded thread-safe Callback-
  Ingress und Worker-Shutdown; SQLite-Journal mit durable Admission/Dispatch/
  Ergebnis und Crash-/Disk-Faults. M1 bleibt unvollständig, M2 folgt erst danach.

### M1-Fortsetzung: dauerhaftes Auftragsjournal — 2026-11-04

- `RobotweaxBridge::journal`: getrennte, exklusiv geöffnete SQLite-WAL-Journale
  mit FULL-Sync, Peer-/Rollenbindung und festen Datensätzen. Sender persistiert
  LOCAL_QUEUED vor Send, Empfänger ACCEPTED vor Antwort und DISPATCHING vor Handler.
- Typisierter SetMeasurementRate-/STATUS-Codec mit stabilen Enumwerten,
  Descriptor-Schemahash und kanonischem Payloadhash; QUERY bleibt leer.
  Session prüft Richtung, Session/Epoch/Domain, Route, Sequenz und Startbudget.
- Neustart: ACCEPTED wird REJECTED/CONTEXT_LOST, DISPATCHING wird UNKNOWN;
  Sender ohne Endbeleg wird UNKNOWN und fragt zuerst ab. Kein automatischer Resend.
  Duplikate verlängern keine Frist, Konflikte ändern keinen vorhandenen Auftrag.
- VFS begrenzt Hauptdatei/WAL/SHM/Rollback auf zusammen 64 MiB logische Längen,
  10.000 Einträge; reservierter Ergebnisraum, keine Evictions. Write-/Sync-Fehler
  sperren auch Reads bis zur Wiederöffnung und Recovery. SQLite-Abhängigkeit 3.45+.
- Fünf SIGKILL-Grenzen prüfen vor/nach Admission, Dispatch und Ergebnis-Commit.
  Kapazitäts-, echte SQLite-VFS-FULL- und injizierte Write-/Sync-Fehler bestanden.
  Keine physische Stromausfall- oder Datenträgerqualifikation.
- Native IPv4/IPv6-Harness: ein Messratenwechsel, Ergebnisnachricht absichtlich
  verloren, CONTROL-Reconnect, QUERY nach 5-s-Budgetablauf, persistiertes SUCCEEDED
  ohne erneute Wirkung. Beide Endpunkte laufen synchron in einem Harness-Prozess;
  Crashtests verwenden separate Kindprozesse. Noch keine ROS-/Geräteanbindung.
- `python3 tools/run_m1.py --native`: Debug 12/12, ASan+UBSan 12/12,
  vollständiger installierter SRT-Build 54/54. [Evidenz](evidence/m1-journal-2026-11-04/README.md)
  enthält Logs, Befehle, Quellhashes und erhaltenen ersten Compile-Fehllauf.
  Kein Commit/Push; Intrinsic unverändert.
- M1 bleibt offen: Produktions-Socket-/epoll-Owner, begrenzter Callback-Ingress,
  beaufsichtigter Journal-/Handler-Worker mit asynchronem Session-/Frische-Fencing,
  ERROR-Wire-Abbildung und integrierter Shutdown-Nachweis binnen fünf Sekunden.

### M1-Fortsetzung: threaded Transport-Owner — 2026-11-05

- `RobotweaxBridge::transport` als eigener installierter-SRT-Target. Ein Thread
  besitzt Sockets, epoll, Session, Queues, Budget und getrennte Reconnectpläne.
  Numerische IPv4/IPv6-Endpunkte, qualifizierte Profile/Buffer/Crypto, nonblocking,
  Linger null; Listener-Sessions und Caller-Binding-IDs werden zufällig erzeugt.
- Feste Try-Lock-Mailboxes: CONTROL 64 FIFO, SENSOR acht latest-only Routenplätze.
  Externe Payloads werden kopiert, ursprünglicher Ingress bleibt erhalten.
  CONTROL-Readiness pausiert vor voller Empfangsmailbox; keine stillen Drops.
- Session-/Kanalgenerationen verwerfen veraltete Arbeit und Workerresultate.
  Automatische Probes starten während Synchronisierung und erneuern Frische;
  unabhängige zufällige Jitterseeds verhindern identische Retryfolgen.
- Native IPv4/IPv6-Tests betreiben zwei echte Owner ohne manuelle Session-/SRT-
  Fortschaltung. SENSOR, QUERY/STATUS, 80 Queries gegen 64er-Mailbox, Ablauf beim
  Poll, >5 s Clock-Erneuerung, kompletter Reconnect, alte Tokens, permanente
  Peerablehnung und vier konkurrierende Produzenten sind abgedeckt.
- Stop bei Verkehr und ausstehenden Verbindungen liegt in den Tests unter fünf
  Sekunden. Noch kein Nachweis für blockierte Journal-/Handler-Worker.
- `python3 tools/run_m1.py --native`: Debug 12/12, ASan+UBSan 12/12,
  Root 56/56 sowie Transport unter ASan+UBSan 2/2 bestanden.
  [Evidenz](evidence/m1-transport-2026-11-05/README.md) enthält die tatsächlichen
  Ergebnisse und bewahrt Compile-/Handshake-Fehlversuche. Kein Commit/Push.
- M1 bleibt offen: begrenzter Journal-/Handler-Worker mit durable Send-Tickets,
  Freigabe vor/nach Dispatch-Commit, ERROR/BUSY/CONFLICT-Wire-Abbildung und
  vollständiger Lifecycle-Qualifikation. Transport empfängt COMMAND, führt aber
  nichts aus; eine COMMAND-Submit-API gibt es ohne diesen Vertrag noch nicht.

### M1-Fortsetzung: Journal-Prozess und durable Send-Tickets — 2026-11-05

- Linux/glibc-Target `RobotweaxBridge::worker` und `robotweax-journal-worker`.
  posix_spawn nach laufenden Transportthreads, private feste 2.048-Byte-IPC-Frames,
  maximal 64 ausstehende Requests. Ein externer Koordinator pollt Antworten;
  Netzwerk-Owner und Parent führen kein SQLite-I/O aus.
- Child benutzt seinen aktuellen Monotonic-Zeitpunkt bei Operationsstart; keine
  vom Parent eingefrorene Zeit kann IPC-Wartezeit aus dem Budget entfernen.
- Nur neu committed LOCAL_QUEUED erzeugt ein einmaliges Sender-Ticket.
  Duplikate, GET, Empfängeradmission, Ablauf und Write/Sync-Fehler tun dies nicht.
  Transport prüft Peer/Epoch/Route/Budget/Kontext, reserviert acht Ingressplätze
  für QUERY/STATUS und verwirft bekannte tote/abgelaufene Tickets vor Send.
- 64 Owner-Check-Slots liefern asynchrone Session-/Frischebeobachtungen vor/nach
  Dispatch-Commit. Sie sind ausdrücklich keine Handler-Startfreigabe.
- Worker-Stop: sofortiger Ticketwiderruf, maximal 2 s Grace, dann SIGKILL;
  einmalige 4-s-Joinfrist. shutdown_timeout behauptet keinen vollständigen Join.
  Tests mit SIGSTOP an fünf Commitgrenzen prüfen Recovery und Stop unter 5 s.
- Native IPv4/IPv6-Integration mit zwei Ownern und getrennten Sender-/Empfänger-
  Prozessen: committed COMMAND-Ticket, dauerhafte ACCEPTED-Rückantwort, begrenzte
  Checks, Ablauf nach Dispatch-Commit, Sessionverlust und UNKNOWN nach Recovery.
  Pausierter Journalprozess blockiert QUERY-Verkehr nicht. Kein neuer Handlerstart.
- Debug 13/13, ASan+UBSan 13/13, Root 59/59, Transport-/Worker-Sanitizer 4/4
  und minimaler macOS-Build 4/4 bestanden.
  Gates und Logs: [Evidenz](evidence/m1-worker-2026-11-05/README.md).
  Reproduktion `python3 tools/run_m1.py --native`; kein Commit/Push, Intrinsic unverändert.
- M1 bleibt offen: automatischer Koordinator samt Sessionverlust-/Query-first-
  Ablauf, final gegen Widerruf linearisierte Startfreigabe, beaufsichtigter Handler,
  ERROR/BUSY/CONFLICT-Wire-Abbildung und vollständiger Bridge-Lifecycle.

### M1-Fortsetzung: automatischer Endpoint und Start-Fences — 2026-11-05

- `RobotweaxBridge::endpoint`: eigener Koordinatorthread mit 64 Inputs, 64 Events,
  64 verfolgten IDs und serieller Command-Pipeline. Durable Admission/Sends,
  ACCEPTED, DISPATCHING, Endstatus, Kontextverlust und Query-first laufen automatisch.
- Frisch committed DISPATCHING mintet ein einmaliges DispatchTicket. Owner koppelt
  es an aktuelle Session-/Frischeprüfung; Child konsumiert einen Shared-Memory-
  Fence per CAS. Widerruf vor Start verhindert Wirkung; RUNNING darf abschließen.
- Sealed memfd mit 64 Slots, 64-Bit-lock-free Atomics, Slotgenerationen, ID-/Hash-
  Bindung, konservativen Deadlines. IPC intern v2, Netzwerkvertrag unverändert.
  Worker-Stop widerruft auch Grants; fehlgeschlagene RUNNING-Slots werden nicht recycelt.
- Grant-Deadline begrenzt durch Command-Budget UND Clock-Qualifikationsgrenze
  (Probe-Alter/Driftbreite). Der Child prüft sie unabhängig vom I/O-Tick; spätere
  Clockprobes verlängern keinen vorhandenen Grant.
- CONTROL-Kontext bindet SID/CONTROL-Generation; SENSOR bindet zusätzlich seine
  Generation. SENSOR-Wechsel allein verwirft keine Steuerarbeit. COMMAND bleibt
  unabhängig von SENSOR-Binding verfügbar.
- Explizit aktivierter simulierter Rate-Handler im Child, absolute Rate mit
  Generationstest und Result-Commit. Zustand initial 200 Hz/Generation 0, nach
  Workerrestart flüchtig zurückgesetzt; Journal bleibt historische Wahrheit.
- Supervisor-/Coordinator-Timeout und gemeinsame Stopsequenz schließen Admission,
  widerrufen ungestartete Arbeit und reapen den Child. Tests unter 5 s, auch mit
  SIGSTOP-Handler, voller Callback-Mailbox und vier Produzenten. Offene lokale
  Benachrichtigungen werden ohne erfundenen Geräte-Endstatus ausgeliefert.
- Debug 14/14, ASan+UBSan 14/14, Root 64/64 und kombinierte Native-Sanitizer 8/8
  bestanden. Neue Race-, Grant-, Endpoint-, Restart-/Query-first- und Shutdown-Evidenz:
  [Koordination](evidence/m1-coordination-2026-11-05/README.md).
  Reproduktion `python3 tools/run_m1.py --native`; kein Commit/Push.
- M1 bleibt offen: allgemeine ERROR/BUSY/CONFLICT/NOT_FOUND-Wire-Antworten und
  abschließende Acceptance-Evidenz. M2 ROS-Node/CDR/Simulator und M4 Intrinsic unverändert später.

### M1-Abschluss: ERROR-Vertrag und installiertes SDK — 2026-11-05

- Separates `errors_v1.proto`: Code, COMMAND-/QUERY-Referenzsequenz, begrenzter
  Backoff. Bestehender Rate-Command-Descriptorhash bleibt unverändert. ERROR ist
  kein Journalstatus und kein Beweis für Ausführung oder Nichtausführung.
- Session/Route/ID/Direction/Epoch/Domain/Replays werden geprüft; Owner korreliert
  gegen 64 Recent-Send-ID/Route-Einträge. ERROR beantwortet kein ERROR.
- Receiver liefert BUSY/CAPACITY/CONFLICT/NOT_FOUND; ausgewählte Frische-/Body-
  Gates liefern Diagnostik. Speicherfehler bleiben fail-closed ohne Antwortgarantie.
- Sender behält Journalwahrheit, meldet peer_error ohne Entry und pausiert Query
  für diese ID/Sitzung. Explizite Query oder Reconnect setzt Reconciliation fort.
  Kein blindes Resend; Endstatus gewinnt gegen späte Fehler. Fremdes STORAGE
  vergiftet nicht das eigene Journal. Vor Admission ist ERROR kein ID-Tombstone.
- Install-/Exportregeln für RobotweaxBridge-CMake-Targets, Worker und Header.
  Voller Linux-SDK-Consumer nach Prefix-Relocation mit echten Sessions/Command/
  Status/Duplikatsperre; Required-Component-Negativfall und ROS/zweiter-SRT-Linkcheck.
  Standalone Minimal-Core samt installiertem Consumer auf macOS arm64 ohne SRT,
  Protobuf/OpenSSL/SQLite/ROS geprüft.
- Debug 15/15, ASan+UBSan 15/15, Root 67/67, Native-Sanitizer 10/10 sowie
  Linux-SDK-Relocation/Consumer/Component-Negativfall bestanden. Host-Minimal-Core
  4/4 plus installierter relocatable Consumer ebenfalls bestanden.
  [Abschluss-Evidenz](evidence/m1-errors-sdk-2026-11-05/README.md) dokumentiert
  tatsächliche Gate-Ergebnisse, unveränderte Providerpins und Install-Artefakte.
  Reproduktion `python3 tools/run_m1.py --native`; kein Commit/Push.
- M1 qualifiziert den ROS-freien Core auf der dokumentierten Linux-amd64-Baseline.
  Kein physischer Geräte-/Netzwerkleistungsnachweis, keine allgemeine Handlerplattform.
  Simulierte Gerätegeneration bleibt nach Workerrestart flüchtig; UNKNOWN wird nie
  automatisch neu ausgeführt. M2/M3/M4 folgen gemäß Architektur.

Der Entwickler ergänzt nach jeder Stufe diesen Abschnitt um tatsächlichen
Commit, Umgebung, ausgeführte Befehle, Ergebnisse, Evidenzpfade, offene Fehler
und den nächsten konkreten Schritt. Bestehende Fehlläufe bleiben erhalten.

M2 ist fertig, wenn ein frischer Entwickler mit den dokumentierten Befehlen
den vollständigen Simulatorlauf reproduzieren kann, alle relevanten Gates
bestanden sind und unbekannte Auftragsergebnisse korrekt sichtbar bleiben.
M3 ist fertig mit einer auswertbaren Vergleichsmatrix, auch wenn diese keinen
SRT-Leistungsvorteil zeigt. M4 erfordert einen tatsächlichen Intrinsic-Lauf.

**Nächster Schritt nach M1 (in M2 umgesetzt):** M2-ROS-Jazzy-Demonstrator auf dem installierten
SDK aufbauen: zwei Nodes in isolierten ROS-Domänen, Imu/JointState mit CDR-/Typ-
Hash-/Größen-/QoS-Gates, ExecuteCommand/GetCommandStatus und echter simulierter
Messratenwechsel samt Generation und Ergebnisbeleg. Lifecycle/Callbacks bleiben
vom SRT-/Journal-I/O getrennt. Intrinsic bleibt M4 im separaten Repository.


### M2 abgeschlossen — ROS Jazzy, 2026-11-05

- Drei ROS-Pakete unter `ros2/`: feste Messages/Services, typisierter Adapter und
  getrennter Sensor-/Messraten-Simulator. colcon baut gegen das installierte SDK.
- Der ROS-freie SDK-Child-Einstieg `RobotweaxBridge::worker_runtime` erlaubt einen
  explizit aktivierten externen Rate-Backend. Der ROS-Worker verwendet den lokalen
  Geräte-Service nach atomarer Startfreigabe. Parent/Child müssen zusammen neu
  gebaut werden: privates IPC jetzt 3, unverändert Wire 1.
- Größen-/UTF-8-/Dimensions-/Typ-Hash-/CDR-Gates und echte lokale QoS-Prüfung
  (Best Effort/Volatile/KeepLast(1)). Fast-RTPS veröffentlicht History-Depth nicht
  im Discovery-Graph; die lokale tatsächliche RMW-QoS wird separat geprüft.
  Leere CDR-Vektoren erfordern getrennte Writer-/gemeldete Größenberechnung;
  der gesamte Serialisierungspuffer wird vorher genullt.
- Publikation prüft direkt vor ROS-Publish Session, Sensor-Generation,
  Publication-Epoch, Clock-Qualifikation und Deadline. ROS-Callbacks führen keine
  SRT-/SQLite-I/O aus; Netzwerk, Koordinator und Geräte-/Journal-Worker sind getrennt.
- Abschlusslauf `.local/m2/20261105T102439657240Z` mit
  `python3 tools/run_m2.py`; vorgelagerter `--build-image`-Lauf ebenfalls bestanden: drei Pakete gebaut, sechs Codec-GTests
  bestanden (colcon zählt zusätzlich den CTest-Wrapper), reale SRT-Verbindung
  zwischen zwei Container-IP-Adressen, DDS lokal und Domänen 41/42 getrennt.
- 626 Imu/350 JointState remote, null direkter DDS-Bypass, ungültige Inputs
  verworfen. Bestätigter Wechsel 200→100 Hz; Generation-Konflikt ohne Wirkung;
  verlorene Antwort nach Wechsel auf 75 Hz ergibt UNKNOWN/effect_uncertain.
  Worker-SIGKILL nach tatsächlichem Wechsel auf 50 Hz/Generation 3: Neustart mit
  neuem SID, QUERY liefert UNKNOWN/context_lost, keine Wiederholung. Vier COMMAND-
  Frames, drei Effekte trotz wiederholter Execute-Aufrufe.
- 2,0011 s Bridge-Unterbrechung; keine alte/doppelte Nutzlast nach Wiederanlauf.
  Saubere Stopps maximal 0,3198 s, Child-Prozesse geerntet. Temporäre Container,
  Netzwerk und Passphrase entfernt; andere Netze unverändert.
- SDK-Regressionslauf `.local/m1/20261105T100528666291Z`: 15 Debug, 15 ASan/UBSan,
  67 native, 10 native ASan/UBSan und relocateter Consumer bestanden. Alle
  archivierten Quellhashes stimmen mit dem aktuellen Code überein.
- Abnahme: `baselines/m2-acceptance.json`,
  `evidence/m2-ros-jazzy-2026-11-05/ACCEPTANCE.md`. Frühere Versuche inklusive
  Fehlläufen bleiben im dortigen `attempts/`-Verzeichnis. M1-Abnahme unverändert.
- Kein Commit/Push: neues Repository weiterhin ohne Commit, Dateien lokal
  untracked. Parent-SRT und Intrinsic-Repository nicht verändert.

**Nächster Schritt:** M3 nach gesonderter Fortsetzung: N0–N5 in isolierter
Kernel-Netzumgebung, Anwendungsalter/Clock-Abdeckung, CPU/RSS/Overhead und
CONTROL-Latenzen erfassen und eine vergleichbare DDS-Baseline bauen. Keine
SRT-Überlegenheit aus M2 ableiten. Der Simulator hält Gerätehistorie nur flüchtig;
physische Geräte, Power-Cut-Qualifikation, lokale DDS-Authentisierung und M4
Intrinsic sind nicht abgenommen. Die ursprüngliche Übernahme bis M2 ist erfüllt.

### M3 begonnen — isolierter Netz-Harness, 2026-11-05

- PR #1 auf ausdrücklichen Nutzerwunsch gemergt: Main-Commit
  `32c53b27839182ec45c448694c60fe1691466118`. Weiterentwicklung auf
  `dev/m3-network-qualification`.
- `tools/run_m3.py` baut ein eigenes SDK-/ROS-Präfix, erzeugt ein internes
  Docker-Netz und neue Endpunkt-Container mit NET_ADMIN; keine Host-qdisc.
  N0/N1/N2/N4/N5 werden als SRT-Entwicklungsläufe unterstützt. Kernel-Readbacks
  prüfen Seeds, Queuegrenzen und Rate. Alte `tc`-Version ohne Seed ersetzt durch
  hash-geprüftes iproute2 6.17.0 im gepinnten ROS-Basisimage.
- ROS-Diagnose ergänzt begrenzte 1-ms-Histogramme konservativer Altersobergrenzen,
  Maximum und separate Sample-Admission-Zähler für Stale/Unknown-Age. Clock-
  Intervallbreite ist konfigurierbar (M2 weiterhin 50 ms, M3 explizit 200 ms bei
  unverändertem 250-ms-SENSOR-Budget). Wire 1 und privates IPC 3 unverändert.
- Stetiger Test hält Sollrate 200 Hz; absolute 200-Hz-Aufträge alle 2 s ändern
  die Generation. UNKNOWN pausiert weitere Aufträge statt eine Generation zu
  raten. Nicht abgeschlossene Aufträge werden getrennt von Latenzperzentilen
  gezählt. Ressourcenbeobachter und rotierte, auf Vollständigkeit geprüfte
  Ethernet-PCAPs zählen DATA/Parität/SRT-Controls getrennt. Kein DDS-Bypass.
- Fünfminütiges N0: `.local/m3/20261105T130451724258Z`, 300,009 s, 150 bestätigte
  Aufträge und genau 150 Effekte; 27.569 Imu/13.709 JointState beobachtet.
  Altersobergrenze IMU p99 15 ms/Max 17,62 ms, Gelenke p99 28 ms/Max 32,65 ms.
  Gleichzeitig fehlen 26.742 IMU im beobachteten Quellzähler-Span von 54.311.
  Capture vor/nach WAN passt; Senke meldet keine Rejections/Ersetzungen. Verlust
  vor WAN (lokaler DDS-Ingress bzw. Latest-only-/Send-Pump-Kadenz) muss vor
  Durchsatzqualifikation genauer zugeordnet werden. 200 Hz sind konfiguriert,
  kein belegtes Erreichen der Sollrate in dieser emulierten Umgebung.
- N1/N2/N4/N5-Smokes bestanden, nur Seedbasis 1701. N4 ist derzeit mittiges
  Kernel-Outage, keine Admission-/Dispatch-/Ergebnis-Commit-Barriere. N5-Prototyp
  mit 256-Paket-Kindqueue hatte Stale/Unknown-Drops und einen offenen Auftrag;
  korrigierte 16-Paket-Kindqueue bestätigte alle acht Aufträge. TBF allein begrenzt
  einen ersetzten Netem-Child nicht auf die angegebene Bytezahl. Paritäts-/DATA-
  Frame-Byte-Verhältnis tatsächlich etwa 0,60 bei kleinen Messages, nicht aus
  einem nominellen 4:1-Paketschema als 0,25 angenommen.
- SDK-Regressionslauf `.local/m1/20261105T124908573510Z`: 15 Debug, 15 ASan/UBSan,
  67 native, 10 native ASan/UBSan und installierter Consumer bestanden.
  Originale M2-Demo `.local/m2/20261105T131111749554Z` ebenfalls bestanden.
  Sieben ROS-GTests plus Wrapper, sechs Python-Harness-Tests bestanden.
- Evidenz/Fehlversuche: `evidence/m3-network-harness-2026-11-05/`; Plan und
  tatsächlich verwendetes Image: `baselines/m3-plan.json`. Roh-PCAPs/JSONL und
  Journale bleiben ignoriert lokal; Artefakthashes liegen in der Evidenz.

**M3 bleibt offen:** N0-Lücken zuordnen und Quellrate/Zeitschnitt/Diagnose-Tail
vollständig zählen; DDS Best Effort und Reliable mit demselben Journalvertrag
implementieren; N3 DATA-/FEC-selektive deterministische Verluste und N4-Barrieren
bauen; vollständige Dauer-/Seed-Matrix ausführen. Keine Leistungsüberlegenheit
behaupten. M4 unverändert später; Parent-SRT nicht verändert.

### M3 N0-Sensorlücken: Hauptursache behoben — 2026-11-05

- 30-s-Attribution mit Quell-Diagnose: 5.461 IMU-/1.481 Joint-Ingress-Callbacks,
  nur zwei BUSY-Abgaben, aber 2.633 Ersetzungen in der Sender-Mailbox. Im
  beobachteten IMU-Span fehlen 2.650 Samples. Der 10-ms-Owner-Wait reduziert
  eine 200-Hz-Quelle im Latest-only-Slot auf ungefähr 100 Hz.
- Native 200-Hz-Regression reproduziert den alten Fehler (100 admitted,
  48 delivered). Aktive Caller fordern jetzt 1 ms Epoll-Timeout an, Listener und
  nicht aktive Caller weiter 10 ms (keine Scheduler-Laufzeitgarantie). Kein Busy-Spin, keine Queue-Vergrößerung,
  keine gelockerten Clock-/Session-/Bandbreiten-/250-ms-Altersgates. Der gepinnte
  SRT-Provider pollt System-Wake-Deskriptoren selbst nur alle 10 ms; der Parent-
  SRT-Code und das qualifizierte Archiv wurden nicht verändert.
- Neue ROS-Diagnose: Ingress pro Route und BUSY/obsolete-Abgaben. Der M3-Observer
  bewahrt Quell-/Senken-/Simulator-Snapshots vor Stop. `gap_attribution` zeigt die
  Stufen, ohne unterschiedlich getimte kumulative Zähler exakt zu bilanzieren.
- Neuer Fünfminutenlauf `.local/m3/20261105T140142459719Z` bestanden:
  IMU 52.793 erhalten, 741/53.534 im beobachteten Quellspan fehlen (1,38% statt
  49,24%); Joint 29/14.576 fehlen (0,20% statt 6,27%). 150 Aufträge bestätigt,
  genau 150 Effekte. Quelle zuletzt 48 BUSY und vier Mailbox-Ersetzungen;
  Senke ohne Admission-Rejection/Stale/Unknown/Ersetzung. Restlücken bleiben offen.
- CPU-Beobachtung auf derselben emulierten Linux-amd64-Baseline: Quelle etwa
  17,35→22,39%, Senke 7,75→10,87% eines VM-Kerns bei erheblich mehr zugestellten
  Daten. Keine kontrollierte Hardware-/DDS-Leistungsvergleichsaussage ableiten.
- SDK-Vollregression `.local/m1/20261105T135638164666Z`: 15 Debug, 15 ASan/UBSan,
  67 native, 10 native ASan/UBSan und Consumer bestanden. Erster San-Lauf blieb
  an einer alten BUSY-Testannahme hängen, nicht an einem Sanitizer-Speicherfehler.
  Reconnect-Negativtests wiederholen nur BUSY und verlangen den ersten anderen
  Rückgabewert OBSOLETE; QUEUED alter Arbeit bleibt Fehler.
- Originale M2-Demo `.local/m2/20261105T135416286568Z` bestanden. Sieben ROS- und
  sieben Python-Tests bestanden. N5-Smoke unter höherer angebotener Last: sechs
  von sieben Aufträgen vor Cutoff bestätigt, sieben Effekte, ein Ergebnis explizit
  offen/zensoriert; keine falsche Erfolgsaussage und kein blindes Replay.
- Evidenz inklusive fehlgeschlagener Regression und Vorher/Nachher-Runs:
  `evidence/m3-sensor-cadence-2026-11-05/`. Source-/Artefakthashes erhalten;
  neue vollständige N0-/SDK-/M2-Manifeste stimmen mit aktuellem Code überein.

**Weiter offen:** verbleibende Rate-/Outbound-Queue-Verluste, exakter Diagnose-
Tail und erreichte Quellrate; danach DDS-Baseline mit gleichem Journalvertrag,
N3-Selektor, N4-Auftragsphasen und volle Seed-/Dauermatrix. M3 bleibt in Arbeit;
Wire 1, privates IPC 3, M4 unverändert. Draft-PR #2 wird mit diesem Fix fortgeführt.

### M3 exakte Sensorfenster und Quellphase — 2026-11-05

- Sensor-Stufenzähler, Pending-Slots und Owner-Epoch per lokalem read-only
  `/bridge/get_metrics`; `/robot/set_publishing` pausiert mit Callback-Fence.
  Frische SRT-Session vor Messbeginn entfernt Warmup-SAMPLE-/FEC-Historie.
  Stabile leere Checkpoints, unveränderte Epochen und sechs Nullresiduen sind
  Pflicht. Fenster-Histogramme stimmen mit Publikationspopulation überein.
- Sender wartet bis zu nahen Pacing-Terminen unter 1 ms, ohne Busy-Spin. Simulator
  erhält Zeitphase, vermeidet Catch-up-Bursts und Phasenreset bei gleicher Rate.
  Strict pacing, Latest-only, Queue-/250-ms-Grenzen und Kryptografie unverändert.
- N0 `.local/m3/20261105T153616391199Z`: 300,097 s, Ist 199,959/49,997 Hz,
  75.011 produziert, 72.372 beobachtet; 2.639 fehlen, alle zugeordnet: 2.542
  Outbound-Ersetzungen, 91 Admission, drei DDS-Ingress, je eine Ingress- und
  Empfangsersetzung sowie ein DDS-Observer-Verlust. Kein SRT-Akzeptanz/Empfang-Gap,
  aber kein Beweis für physisch verlustfreies WAN. 150 bestätigt/150 Effekte.
- N4-Smoke `20261105T154538668977Z`: sieben bestätigt/ sieben Effekte. N5-Smoke
  `20261105T154456488682Z`: zwei bestätigt/zwei Effekte, ein Auftrag offen;
  Bilanz-Pass ist keine Auftragsabnahme. Ergebnisse werden bis acht Sekunden nach
  Cutoff abgefragt und pro Zeile markiert; gepoolte Latenzen enthalten Drain.
- SDK `.local/m1/20261105T145359704756Z`: 15/15/67/10 Tests und Consumer bestanden.
  M2 `.local/m2/20261105T154053788107Z` bestanden; sieben Codec-/vier Schedule-
  GTests, elf Python-Tests. Finale Source-Hashes geprüft. Ein vorheriger M2-Lauf
  scheiterte an Image-Pin-Preflight; spätere Inspects und unveränderter Retry
  bestanden. Ursache unbekannt, Assertion nicht gelockert; Evidenz erhalten.
- Evidenz `evidence/m3-window-accounting-2026-11-05/` bewahrt finale Manifeste,
  Entwicklungsläufe, Tests, Artefakthashes und Grenzen. CPU/Wire umfasst weiterhin
  Gesamtbeobachtung; N0 überlappte teilweise mit M2 in derselben VM. Keine
  kontrollierte CPU- oder Überlegenheitsaussage. Frühere Marker-Spans bei ~178 Hz
  sind nicht direkt mit dem neuen 200-Hz-Fenster vergleichbar.

**Nächster Schritt:** DDS Best Effort + Reliable mit gleichem Journalvertrag und
Messfenster implementieren; CPU/Wire zeitlich angleichen, N3-DATA/FEC-Selektor,
N4-Auftragsphasen und volle Seed-/Dauermatrix. Outbound-Ersetzungen bei echter
200-Hz-Last und N5-Auftragsabschluss weiter qualifizieren. M3 bleibt in Arbeit,
Draft-PR #2 bleibt offen. Parent-SRT, Wire 1, privates IPC 3 und M4 unverändert.

### M3 DDS-Sensorpfad implementiert — 2026-11-05

- `tools/run_m3_dds.py` und separater DDS-Driver betreiben direkte typisierte
  Best-Effort/Volatile/KeepLast(1)-Sensoren in internem Docker-Netz, Domäne 60,
  explizite statische Peers. Multicast allein lieferte in diesem Lab keine
  Discovery; Timeout ist erhalten. Kein SRT-Prozess, keine Host-qdisc/Ports.
- Source-Fences und stabile Observer-Snapshots bilanzieren tatsächlich erzeugte,
  empfangene, akzeptierte, stale/invalid/clock-rejected Samples. Fehlend vor
  Callback umfasst Middleware/Kernel/Netz/History, keinen isolierten WAN-Verlust.
  Discovery prüft Best Effort/Volatile; History/Depth kann UNKNOWN sein.
- N0 30 s `.local/m3-dds/20261105T161851009485Z`: 6.023 IMU + 1.507 Joints erzeugt
  und alle empfangen, Ist 199,891/50,014 Hz. Gemeldeter Mindest-Offset-Schritt
  1.281.694 ns disqualifiziert Altersmetriken; 3.152 folgende Samples am Clock-
  Gate verworfen. Ursache nicht belegt. Count-Pass ist keine Altersabnahme.
- N1-Smoke `.local/m3-dds/20261105T161943936259Z`: 3.022/756 erzeugt, 2.079/746
  empfangen/akzeptiert; 943/10 vor Callback fehlen. Lokale Shared-VM-Alterschecks
  bestanden, aber weder konservative SRT-Clock-Grenze noch gleicher Zeitursprung:
  DDS nutzt Simulator-Header, SRT Bridge-Ingress. Kein Leistungsvergleich.
- Ungeklammerte Clock-Reads hatten Scheduling als Sprung fehlklassifiziert;
  geklammerte Intervalle trennen Read-Unsicherheit, Drift und gemeldete Schritte.
  Ein Fünfminutenversuch scheiterte am ursprünglichen harten Clock-Gate und
  bewahrte keine finalen Zähler: daraus keine Sample-Zahlen ableiten. Der finale
  Runner bewahrt Zähler und begrenzte Sprungdiagnose, markiert Alter separat.
- DDS-Capture zählt IPv4-Fragment-Frames separat ohne RTPS-Payload-Zuordnung.
  SRT bleibt standardmäßig strikt; Reparse des alten vollen N0 ergibt identisch
  156.443 Frames je Endpunkt und identische Summary-Felder. Beide finalen DDS-
  Captures vollständig und ohne Kernel-Capture-Drops. 19 Python-Tests bestanden;
  installierter Driver/Helper bytegleich und Import/Help bestanden. Keine SDK-
  oder ROS-C++-Änderung, außer Installation der neuen Python-Tools.
- Evidenz: `evidence/m3-dds-sensors-2026-11-05/`. Finale Läufe wiederverwenden
  Simulator-Binary explizit, Hash erhalten; alle 124 Inventar-Sourcehashes passen.
  Fehlversuche und Rohcapture-Hashes erhalten, PCAPs bleiben ignoriert lokal.

**Weiter:** vollständig journalisierten Reliable-DDS-Auftragskoordinator bauen,
mit dauerhaftem Sender-Admission vor Send, frischer Session/Clock-Autorisierung
vor DISPATCHING/Handler-Start, identischem Journal/Handler, QUERY/UNKNOWN und
keinem Replay alter Absicht nach Reconnect/Crash. Direkter Apply-Service-Aufruf
ist kein Ersatz. Sensor-Runner sendet keine Aufträge und nutzt keine DDS-Krypto;
Command-/Security-/Age-/CPU-/Wire-Vergleich und voller Seed-/Dauerlauf fehlen.
N2/N5 sind im neuen Runner implementiert, hier noch nicht ausgeführt; N3 und N4-
Auftragsphasen weiterhin offen. PR #2 bleibt Draft, M3 nicht abgenommen.

### M3 Reliable-DDS-Auftragsjournal implementiert — 2026-11-05

- `dds_command_node` + `tools/run_m3_dds_commands.py`: feste Reliable/Volatile/
  KeepLast(64)-Frames, pro Endpunkt eigener Journal-Thread, Route 100, Budget
  5.000 ms. SDK-`CommandJournal` unverändert; `RosRateBackend` in geteilten Header
  verschoben und identisch vom bisherigen SRT-Worker und DDS genutzt.
- Neue Sender-Admission vor einzigem COMMAND; Duplikat/Recovery nur GET/QUERY.
  Empfänger committet Admission/DISPATCHING, prüft vor atomarem Start unter dem
  Session-Mutex Live-Lease, Epochen, Deadline. Kein Disk-/Handler-Aufruf unter
  diesem Mutex. Bereits beanspruchter Start kann bei späterer Revokation Effekte
  haben; fehlendes Resultat bleibt UNKNOWN. SRT-Ticket-/IPC-Fences unverändert.
- Common-VM-only: lokaler Boot-/Time-Namespace-Digest muss auf beiden Seiten
  passen. Acknowledged Session aus Prozess-/Link-Nonces, Sequenz-/Frischechecks,
  1,5-s-Lease; Ablauf ändert lokale Link-Nonce. 64 retired Peer-Nonces verhindern
  Rollback; Kapazität erschöpft → Fail-Closed. Keine DDS-Krypto-/Cross-Host-
  Authentisierungs-/Clock-Abnahme. Keine vorgetäuschten SRT-Security-Flags.
- Final `.local/m3-dds-commands/20261105T175009991487Z` bestanden: ID 1 100 Hz
  SUCCEEDED, Duplikat ohne neuen Send/Effekt, andere Payload desselben IDs meldet
  lokalen Konflikt. ID 2 75 Hz bewirkt Effekt, verspätete Antwort → UNKNOWN.
  ID 3 50 Hz bewirkt Effekt, Receiver SIGKILL und Sender SIGKILL vor Reconciliation;
  nach Reopen QUERY → UNKNOWN/context_lost, kein altes COMMAND. Nach expliziter
  Device-Reconciliation und Reset der Fault-Verzögerung neue ID 4 200 Hz SUCCEEDED.
  Insgesamt vier Absichten/vier Effekte; drei COMMANDs vor Sender-Crash, danach
  ein QUERY und nur das neue COMMAND ID 4. Zwei UNKNOWN haben kein gültiges Resultat.
- Read-only SQLite quick_check nach Cleanup auf beiden Journals bestanden:
  identische vier IDs, Payload-Hashes, Revision 3, Status-/Result-Felder. Captures
  vollständig: Robot 5.107 / Operator 5.081 Frames, keine unzugeordneten Frames
  oder Kernel-Capture-Drops. Sender meldet nach Restart einen Callback-Admission-
  Drop, Typ unbekannt; nicht als WAN-Verlust oder garantiertes Admission auslegen.
  Handler/Journal können ausgehende HELLOs verzögern und konservativ Lease drehen.
- Sieben neue Session-GTests + sieben Codec + vier Schedule bestanden (18 echte,
  21 inklusive Wrapper). 19 Python-Tests bestanden. Originales vollständiges M2
  `.local/m2/20261105T175011079038Z` nach Handler-Extraktion bestanden. Finale
  DDS-/M2-Source-Inventare 132/81 Dateien passen. SDK-Source/Wire 1/IPC 3 unverändert.
- Evidenz `evidence/m3-dds-commands-2026-11-05/` inklusive Journal-Inspektion,
  Artefakthashes und früherem Fault-Test, der UNKNOWN korrekt lieferte, weil die
  Testverzögerung für neue Arbeit noch aktiv war. Test setzt sie jetzt explizit
  zurück. Roh-Journale/PCAPs bleiben lokal ignoriert. Auftragsresultate stammen
  aus DDS-Status; Dateien tragen Teststeuerung und Geräte-Diagnosen.

**Nächster Schritt:** diesen journalisierten Koordinator mit stetiger 200/50-Hz-
DDS-Sensorlast und absoluten 200-Hz-Absichten alle 2 s zusammenführen. Danach
N0/N1/N2/N4/N5 mit denselben Fenstern, CPU-/Wire-Scope und Ergebnis-Drain wie SRT
qualifizieren; Clock-Ursprung/-Grenzen und Kryptografie vergleichbar machen.
N3-DATA/FEC-Selektor, N4-Admission/Dispatch/Result-Commit-Barrieren und volle
Seed-/Dauermatrix offen. M3 bleibt in Arbeit, PR #2 Draft; keine M4-Änderung.

### M3 stetige DDS-Sensor-/Auftragslast zusammengeführt — 2026-11-05

- `tools/run_m3_dds.py --commands`: Quelle 200/50 Hz, absolute 200-Hz-Aufträge
  alle 2 s. Ein Pending, keine Catch-up-Bursts, UNKNOWN/Pending blockiert weitere
  Absichten. Freie Slots fragen Execute trotz NOT_READY-Diagnose an; explizite
  Non-Admissions werden gezählt. Sensor-only ohne Flag bleibt erhalten.
- Vor Beginn beide Journal-Koordinatoren bereit, keine Auftragshistorie/Effekte.
  Sensor-Fences unverändert; Cutoff stoppt neue Aufträge, Ergebnisbeobachtung
  maximal bis Cutoff+8 s, danach eingefroren. Separate letzte Device-Fence für
  Effekte/Generation; Sensorzähler dürfen nicht mehr steigen. Owner-Epochen
  müssen gleich bleiben. Auftragsdiagnosen behalten 100-ms-Snapshot-Scope.
- Erster langer Lauf `20261105T181542377101Z`: nur zwei bestätigt/ein offener
  Auftrag, Sender/Empfänger mit 30/18 Callback-Drops. Code konnte schon empfangene
  Reliable-Frames bei Try-Lock-Contention verlieren. Kurze Validierungs-/Kopier-
  abschnitte serialisieren jetzt, ohne Disk/Handler/Netz unter Mutex. Inbox bleibt
  64; voller Puffer zählt Drop. Lokale Service-Admission bleibt Try-Lock/BUSY.
  Neuer Parallelproduzenten-Test prüft 64 Aufnahmen ohne Contention-Verlust.
  Keine Queue-, Lease-, Clock- oder Deadline-Lockerung und kein Intent-Replay.
- N1-Capture deckte gültiges 4-Byte-Endfragment auf: es besitzt keinen UDP-Header.
  Parser prüft IP-/Fragment-Länge und MF-Ausrichtung, verlangt UDP-Header nur wo
  vorhanden. Regression getestet; alte SRT-N0-Summaries weiter identisch. Alte
  Manifeste unverändert; separate Reanalyse dokumentiert den Fix.
- Finales N0 `.local/m3-dds-combined/20261105T183834692545Z`: 300,127 s, Ist
  199,978/50,002 Hz, 75.026 erzeugt/75.025 empfangen, ein IMU fehlt vor Callback.
  150/150 bestätigt und 150 Effekte, keine Inbox-Drops. Beide geschlossenen
  Journale quick_check ok, dieselben 150 Payload-Hashes/Revisionen 3/SUCCEEDED,
  Rate 200 und Generationen 1–150. Alter nach Clock-Schritt unqualifiziert:
  54.313 IMU/13.580 Joint-Callbacks clock-rejected; empfangene Callbacks, kein
  isoliertes Netzverlustmaß.
- Finale Smokes, jeweils 15 s und Seed 1701:
  N1 `20261105T184311488522Z`: 7/8 bestätigt, eine Non-Admission, sieben Effekte.
  N2 `20261105T184014775290Z`: 1/2 bestätigt, ein Pending, sechs Slots blockiert.
  N4 `20261105T184051558249Z`: 4/5 bestätigt, ein Pending, drei Slots blockiert;
  mittiges Kernel-Outage, keine präzisen Auftragsphasen-Barrieren.
  N5 `20261105T184126432851Z`: fehlgeschlagen nach 45 s Sender-Ready-Wartezeit im
  Cold-Start unter dem unveränderten 512-kbit/128K-Konkurrenz-Profil; kein Messfenster.
  Nicht als vollständige Auftrags-/M3-Abnahme auslegen, keine Nullwerte erfinden.
- Korrigierter C++-Build `20261105T182432483577Z`: 19 echte ROS-GTests, 22 mit
  Wrappern bestanden. 27 Python-Tests bestanden. Finale Sensor-only-Regresssion
  `.local/m3-dds/20261105T184339550820Z` und DDS-Fault-Acceptance
  `.local/m3-dds-commands/20261105T184405437225Z` bestanden. Finale Läufe verwenden
  dieses aufgezeichnete Binary wieder; alle 136 Sourcehashes passen, installierte
  Python-Dateien bytegleich. SDK/SRT-Source und Wire 1/IPC 3 unverändert.
- Evidenz `evidence/m3-dds-combined-2026-11-05/`: auch Fehlversuche, Parser-Reanalyse,
  Journalprüfung und Rohartefakthashes. N0 lief zeitweise parallel zu Entwicklungs-
  fixtures; keine kontrollierte CPU-/Hardware-Aussage, keine Überlegenheit.

**Weiter:** DDS-Ready-/Completion-Grenzen unter N1/N2/N5 untersuchen, ohne die
Sicherheitsgates oder No-Replay zu lockern. Altersursprung/-Qualifikation und
Kryptografie vergleichbar machen; CPU/Wire an dieselben Fenster koppeln. Danach
volle Seed-/Dauermatrix, N3-DATA/FEC-Selektor, N4-Admission/Dispatch/Result-Commit-
Barrieren. M3 bleibt in Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.


### M3 DDS-Readiness und Lifecycle nachgebessert — 2026-11-05

- Nach Lease-Ablauf fehlte die erneute Zielsuche: beide Enden konnten HELLOs an
  pensionierte Peer-Links senden. Jetzt zunächst leeres Discovery-Ziel, dann
  weiterhin gegenseitige Bestätigung der aktuellen Nonces; alte Links bleiben
  retired. Simultane und einseitige Abläufe durch deterministische GTests geprüft.
- HELLO auf separater BestEffort/Volatile/KeepLast(1)-Spur mit eigenem 100-ms-
  Thread. Reliable/Volatile/KeepLast(64) für COMMAND/QUERY/STATUS/ERROR bleibt.
  Strenge Replay-Cursor pro Spur verhindern, dass neue HELLOs ältere gültige
  Controls verwerfen. Tatsächliche lokale QoS beim Start geprüft. Beide DDS-
  Enden gemeinsam neu bauen (neues owner_ready-Feld), SDK-Wire 1/IPC 3 gleich.
- Journal-/ROS-Handler-Eligibility ist Teil der Bereitschaft und wird im HELLO
  gemeldet; lokale Start-Prüfung bleibt. Diagnosen für Matches, HELLOs, Ablehnung,
  Lease-Abläufe und Epochen ergänzt. Kein Lock über Journal, Handler oder Netz.
- Shutdown-Repeats fanden einen intermittierenden >5-s-Timeout. Pre-Shutdown
  stoppt/ joint Threads vor Middleware-Shutdown; verschachtelter Handler-Context
  gehört jetzt der Node und wird außerhalb des gejointen Workers zerstört.
  Drei aufeinanderfolgende finale Fault-Läufe bestehen inklusive 5-s-Gate,
  Duplikat/Konflikt, verzögerter Antwort UNKNOWN, Receiver-/Sender-SIGKILL,
  Reopen/QUERY ohne altes COMMAND und neuer Absicht nach Device-Reconciliation.
  Beim blockierten Handler bleiben beide Lease-Zähler 0 → 0. Vorherige Timeouts
  bleiben Evidenz; kein Debugger-Stack beweist einen bestimmten Middleware-Lock.
- Testharness wartet auf kumulative Diagnosen vor Send-Assertions. Atomare
  Phase-Dateien tolerieren kurz fehlende Datei beim Lesen, kein exists/open-Race;
  kaputtes JSON bleibt Fehler. Phasen-ID steigt im Speicher. Dateien sind kein
  Ersatz für DDS-Auftragsresultate. 23 echte ROS-GTests/26 mit Wrappern und
  30 Python-Tests bestanden; vollständiges originales M2 erneut gebaut/bestanden.
- Finaler N1-Smoke 8/8 bestätigt. N2 (60 s) 17/18 bestätigt, ein offen/17 Effekte,
  zwölf Slots blockiert; beide Enden am Ende ready, keine Lease-Abläufe. N4-Smoke
  4/5 bestätigt/ein offen/vier Effekte, beide Enden nach je einem Lease-Ablauf
  wieder ready. Kein Replay der offenen Absichten. Früherer N2-Entwicklungslauf
  schaffte 28/28; variable Completion bleibt sichtbar, keine Vollabnahme.
- Explizites `--startup control-first`: Sensorquelle bleibt bis Ready aus,
  Nullproduktion geprüft, dann Warmup und gleiche Fences. Impairment und N5-
  Konkurrent schon aktiv. Finaler N5-Smoke zwei bestätigt/zwei Effekte, sechs
  Slots blockiert. Kein Nachweis für Beitritt bei bereits laufender Telemetrie.
  Default bleibt simultaneous. `--dds-profile udp1200` ist zweite explizite
  Variante; keine IP-Fragmente im Entwicklungscapture, N5-Start trotzdem gescheitert.
  Default bleibt system. Keine Queue-/Lease-/Frische-/Deadline-Lockerung.
- Evidenz `evidence/m3-dds-readiness-2026-11-05/`: finale Manifeste/Sourceprüfung,
  vorherige Fehlversuche, gemischte Completion, Paketfeld-Analyse, Rohartefakthashes.
  Roh-PCAPs/Journale lokal; ältere Evidenz unverändert. Zwei M2-Aufrufe scheiterten
  vor Build am unveränderten Image-ID-Gate; Read-only-Rechecks passen, unveränderte
  vollständige Wiederholungen bestanden. Ursache unbewiesen, Gate bleibt streng.

- Finales fünfminütiges N0 `20261105T201220121826Z`: 150/150 bestätigt, 150 Effekte,
  Ist 199,976/50,002 Hz; 75.025 produziert/75.022 empfangen, drei IMU vor Callback
  fehlen. Lokale Alterschecks bestanden, keine Cross-Host-Aussage. Beide Journale
  quick_check ok, identische 150 SUCCEEDED/Revision-3-Records und Generationen
  1–150. Inbox-Drops/Lease-Abläufe jeweils null. Finale elf Manifeste (inklusive
  N5-Fehler) passen: DDS 138/M2 86 Source-Dateien, installierte Python-Dateien
  bytegleich. Binary-Build `201016201590Z`, Fault-Repeats `201144179119Z` und
  `201202123026Z`; M2 `201220118978Z`. Keine kontrollierte CPU-/Hardware-Messung.

**Weiter:** offene DDS-Aufträge trotz bestehender Readiness unter N2 und belasteten
simultaneous-N5-Start untersuchen; keine Absichten blind erneut senden. Clock-/
Crypto-Gleichheit und gemeinsame CPU-/Wire-Fenster qualifizieren, danach volle
Seed-/Dauermatrix, N3-DATA/FEC-Selektor und N4-Auftragsphasen-Barrieren. M3 bleibt
in Arbeit, PR #2 Draft, SRT/SDK unverändert, Intrinsic/M4 weiterhin unberührt.


### M3 offene DDS-Aufträge auf Paketfrische zurückgeführt — 2026-11-05

- Frühere N2-Captures/geschlossene Journale read-only analysiert: ID 18 lokal
  LOCAL_QUEUED/Revision 0, kein Empfängereintrag; erster beobachteter COMMAND
  relativ zum lokalen HELLO-Zeitoffset etwa 2,13 s alt, danach NOT_FOUND-ERRORs.
  Das isoliert keinen Netzanteil. Originale Evidenz und Rohartefakthashes erhalten.
- Neue Session-Validierungsdiagnosen mit erstem Ablehnungsgrund: accepted,
  session, peer, clock, sequence, invalid_time, stale. Letzter stale COMMAND
  erhält ID/Send-/Ingresszeit. accepted ist weder Journal-Admission noch Start.
  Receipt-gematchte NOT_FOUND-Antworten und maximale Reliable-Publish-Aufrufdauer
  getrennt gezählt. Feste Counter/Snapshots, kein unbegrenztes Event-Logging.
- Workload speichert letzte lokale Status-/Fehlerbeobachtung auch beim offenen
  Intent. found bezieht sich auf lokales Journal; NOT_FOUND kann vom Peer gecacht
  sein. budget_elapsed meint 5 s seit lokalem Client-Aufruf, keine autoritative
  Empfänger-Expiration. Timeout/NOT_FOUND erzeugen keinen Terminalzustand und
  erlauben kein Replay. Der einzelne offene Auftrag blockiert weiter neue Slots.
- Drei finale N2-Probes je 60 s: Seed 1701 2/3 bestätigt, ein offen/zwei Effekte;
  Seed 2903 28/28 bestätigt/28 Effekte; Seed 4211 11/12 bestätigt, ein offen/elf
  Effekte. Bei 1701/4211 je ein COMMAND direkt am Callback mit 2.212,649 bzw.
  2.474,505 ms Alter verworfen, noch vor der 5-s-Startdeadline. Stale-ID entspricht
  offenem Intent; kein Empfängereintrag, später 247/171 gematchte NOT_FOUNDs.
  Beide Enden bleiben ready. Maximale Sender-Publish-Aufrufe unter 1 ms; kein
  Beleg für blockierenden Publish als Ursache dieser beiden Fälle. Middleware-
  Repair/Queue/Transport/Executor noch nicht einzeln isoliert. Kein 600-s-Gate.
- N0 30 s: 15/15 bestätigt/15 Effekte, keine stale Commands. N4-Smoke 4/5/ein
  offen, beide Enden wieder ready; Kontextablehnungen während Outage, kein
  stale-COMMAND-Inkrement. N5 simultaneous erneut vor Fenster gescheitert:
  beide Enden ohne Matches/empfangene HELLOs. Discovery bleibt offen.
- Vollständige DDS-Fault-Acceptance nach Build `20261105T203710218043Z` bestanden,
  einschließlich Duplikat/Konflikt, verlorener Antwort UNKNOWN, Receiver-/Sender-
  SIGKILL, Reopen/QUERY ohne Intent-Replay, neuer Absicht nach Reconciliation und
  5-s-Shutdown. 24 echte ROS-GTests/27 mit Wrappern und 32 Python-Tests bestanden.
  Deterministischer Test prüft jeden Rejection-Grund, exakte Stale-Grenze, lebende
  HELLOs und unveränderten Replay-Cursor nach Ablehnung. Beobachtungstests erzeugen
  keinen Terminal-/Result-/Nichtausführungsnachweis aus NOT_FOUND oder Timeout.
- Evidenz `evidence/m3-dds-completion-2026-11-05/`: sieben finale Source-Inventare
  und Binaryhashes passen, installierte Python-Dateien bytegleich. SDK/SRT/Wire 1/
  IPC 3 unverändert. Die volle M2-/5-min-N0-Evidenz bleibt historisch bei 940b4cb;
  diese Diagnose-Stufe wiederholt sie nicht. Keine Clock-/Crypto-/CPU-/Wire-Parität.

**Weiter:** belastbare empfangsseitige Reconciliation für nie admittierte Absichten
spezifizieren/prüfen; bloßer Timeout oder NOT_FOUND reicht nicht. Keine alte
Absicht erneut senden, keine Frische-/Start-Gates lockern. N5-Discovery, dann
vergleichbare Clock-/Crypto-/CPU-/Wire-Fenster und volle Matrix. PR #2 bleibt Draft,
M3 offen, Intrinsic/M4 unverändert.

### M3 DDS-Protokoll v2: empfangsseitige Expiry-Versiegelung — 2026-11-05

- `SEAL_EXPIRED` ist strikt nicht ausführend. Der Sender kann es nur für
  LOCAL_QUEUED/Revision 0 ohne bestätigte Receiver-Admission in ursprünglichem
  Owner/Prozess und derselben live Session senden, strikt nach gespeicherter
  5-s-Deadline. Nach Prozess-/Session-Wechsel bleiben alte Absichten QUERY-only.
  Alle DDS-Frames einschließlich HELLO verlangen Protokollversion 2; beide Enden
  neu bauen, kein Downgrade. Keine SDK-Wire-/IPC-/SRT-Änderung.
- Neuer ROS-Helper nutzt ausschließlich die öffentliche, unveränderte SDK-
  Journal-API. Existierender Record wird unverändert geliefert (auch ACCEPTED,
  DISPATCHING, SUCCEEDED, UNKNOWN); widersprüchliche Metadaten sind Konflikte.
  Nur fehlende ID nach Deadline erzeugt per vorhandener FULL-synchroner Admission
  EXPIRED/START_DEADLINE, Revision 1, ohne Dispatch/Resultat. Commit vor STATUS.
  Kein Handlerpfad; späteres COMMAND findet das ID-/Hash-Tombstone und startet
  nicht. Journal-Records werden in der Session nicht eviziert. Context-Verlust
  während Commit kann nichts ausführen; unbekannte Historie in neuem Kontext
  wird nicht als Expiry ausgegeben. Bestehendes Tombstone bleibt per QUERY lesbar.
- Separate Seal-Sent/Received/Inserted/Existing/Rejected-Zähler. Vorhandener
  Record ist keine neue Expiry. Ausführbares COMMAND wird nicht erneut publiziert;
  Reliable-DDS-Paketretransmission bleibt erlaubt. Timeout/NOT_FOUND allein sind
  weiterhin kein Terminalresultat. Erst bestätigter Receiver-Status beendet die
  Unsicherheit; Lab-Cadence darf danach neue ID ohne Generationserhöhung anbieten.
- Drei N2-Probes je 60 s: 1701 24 SUCCEEDED/24 Intents; 2903 28 SUCCEEDED plus
  eine EXPIRED/29; 4211 24 SUCCEEDED plus eine EXPIRED/25. Alle ohne offene Intents.
  Beide Expiry-IDs auf beiden Seiten Revision 1, identische Hashes/Generation,
  keine Dispatch-Zeit/kein Resultat; Receiver-Admission strikt nach Deadline.
  Bei 4211 verfällt ID 20, neue geplante ID 21 gelingt mit expected generation 19
  und result generation 20. Insgesamt 25 COMMAND-Publikationen/25 neue Intents,
  nur 24 Starts/Effekte. Bei 1701 liefert Seal echten schon committeten Erfolg;
  keinerlei Überschreiben nach Deadline. Kein deterministischer Paket-Replay-
  Vergleich mit alten Seeds und kein 600-s-Abnahmegate.
- Fünfminütiges N0 `20261105T205705247794Z`: 150/150 SUCCEEDED/150 Effekte,
  keine Seals. Ist 199,984/50,001 Hz; 75.024 produziert/75.002 empfangen, 20 IMU-
  und zwei Joint-Gaps vor Callback. Lokale Shared-VM-Alterschecks bestanden,
  keine isolierte WAN-Verlust-/Cross-Host-/Hardware-Aussage. Beide Journale stimmen
  in allen 150 Resultaten überein, quick_check bestanden.
- N4-Smoke bleibt 4/5 SUCCEEDED/ein offen, beide Enden nach Outage wieder ready;
  keine Seals über den Context-Wechsel. N5 control-first zwei SUCCEEDED/zwei
  Effekte, 31 Seals auf vorhandene Records, kein falsches EXPIRED, sechs Slots
  blockiert. N5 simultaneous erneut fehlgeschlagen vor Messfenster; Discovery offen.
- Acht neue tatsächliche SDK-Journal-GTests: Deadline-Grenze, Metadaten/Context,
  Tombstone/Duplikat/später Dispatch, vorhandene Zustände, Konflikte, Sender-
  Eligibility, verlorener Reply mit Owner-Reopen/QUERY, Speicherfehler. Insgesamt
  32 echte ROS-GTests/36 mit Wrappern und 33 Python-Tests bestanden. DDS-Fault-
  Acceptance einschließlich Receiver-/Sender-SIGKILL/UNKNOWN/No-Replay und volle
  originale M2-Neubau-/Runtime-Regression bestanden.
- Evidenz `evidence/m3-dds-expiry-seal-2026-11-05/`: neun finale Source-Inventare
  passen (DDS 140/M2 88), Binaryhash identisch, installierte Python-Dateien
  bytegleich. C++-Build `205428937697Z` hat ausschließlich spätere nicht kompilierte
  Änderungen an zwei Runner-Metadaten und Host-Testdatei; alle kompilierten Inputs
  passen. Finale Fault-/M2-Läufe `205705247608Z`/`205705247870Z`. SDK-Archivhashes
  gegen b8e198d identisch, Core/Proto und SRT-Quelle unverändert. Roh-PCAPs/Journale
  lokal, Hashes/Größen erhalten. Frühere Evidenz unverändert.

**Weiter:** Kontext-/Owner-wechselnde Unsicherheit bleibt explizit offen; keinen
Abwesenheitsnachweis aus einem neuen leeren Journal ableiten. N5-Discovery und
SRT-Parität der neuen Reconciliation-Semantik/-Kosten qualifizieren, danach
Clock-/Crypto-/CPU-/Wire-Gleichheit und volle Matrix. M3 offen, PR #2 Draft,
Intrinsic/M4 unverändert.

### M3 explizites DDS-Sensor-Pacing für N5 — 2026-11-05

- Neue optionale `--dds-profile paced-sensors` in Combined- und Fault-Runner.
  Default bleibt system. Keine ROS-/Core-/SDK-/SRT-/Protokolländerung; unveränderte
  kompilierte Inputs/Binaries seit 02d40e6. Keine Gates gelockert. Normale
  Nicht-skip-Builds bauen die separate Native-Probe automatisch; Preflight bei
  jeder paced-Ausführung, auch bei dokumentierter Binary-Wiederverwendung.
- XML: gleiche UDPv4/SHM-1200-Paketisierung wie vorheriger negativer Versuch,
  nur `/robot/imu` und `/robot/joint_states` asynchron auf gemeinsamem Controller
  1600 Byte/50 ms pro Simulator-Participant. Kein Ethernet-/globales Budget oder
  TC-Prioritätsbypass. Source bleibt 200/50 Hz, Sensor-QoS BE/Volatile/KeepLast(1),
  Controls Reliable/Volatile/KeepLast(64) synchron auf Default-Controller.
  RMW-XML-Opt-in nur für diese Variante; PREALLOCATED_WITH_REALLOC und DataSharing
  OFF explizit erhalten, SHM-Transport weiter aktiv.
- Standalone-C++-Probe nutzt öffentliche RMW/Fast-DDS-Handles für reale Controller-
  und Writer-QoS. Positive Prüfung und Build-Rezept bestanden. Ohne XML-Opt-in
  verweigert Provider die Writer-Erzeugung. Probe läuft vor Laborerzeugung in
  eigenem network-none-Container, ohne Discovery-Warmup gemessener Peers.
  Sie wird nicht in Bridge/Simulator gelinkt; Fast-DDS-spezifisches Lab-Werkzeug.
- N5-Runner prüft jetzt lebenden Konkurrenten während Szenario-Polls sowie UDP,
  Ziel 128.000 bit/s, 1024 Byte und plausibles gesamtes tatsächliches Angebot.
  Cleanup-SIGINT akzeptiert; anderer Fehler/fehlende Last scheitert. Kein Beleg
  fenstergenauer Zustellung. TBF 512 kbit/s/Netem 16 und Konkurrenz bleiben vor
  Source-/Koordinatorstart aktiv; kein control-first-Publikationsstopp.
- Fünfminütiges N5 simultaneous/paced `20261105T214042516097Z`: 150/150 bestätigt,
  150 Effekte, keine Lease-Abläufe/Inbox-Drops/Seals, beide Enden ready. Source
  Ist 199,993/50,002 Hz, 60.019 IMU/15.006 Joints produziert, 11.752/7.376 Callbacks.
  Alle 19.128 empfangenen Samples bestehen lokale Alterschecks. 55.897 fehlen
  vor Callback inklusive beabsichtigter Middleware-Pacing-/Ersetzungsanteile;
  kein isolierter WAN-Verlust. Beide geschlossenen Journale quick_check ok,
  identische 150 SUCCEEDED/Revision-3-Records, Resultgenerationen 1–150.
  Konkurrenz gesamt 128.009,2 bit/s, 1250 lebende Prozess-Polls.
- Drei paced-N5-Smokes, Seeds 1701/2903/4211, je 8/8 bestätigt/acht Effekte.
  Frische System- und UDP1200-N5-Runs scheitern vor Messfenster trotz validierter
  Konkurrenz. Pacing ist expliziter Baseline-Kandidat, kein Default-Fix und kein
  verlustloses Ergebnis. N0 system, N0 paced, sensor-only paced und paced-N0-
  Fault-Acceptance mit Duplikat/Konflikt/UNKNOWN/SIGKILL/QUERY/No-Replay/5-s-Shutdown
  bestanden; blockierter Handler lässt Leases unverändert. 35 Python-Tests bestanden.
  Die 32 ROS-GTests/volle M2-Regression bei 02d40e6 bleiben historische Evidenz,
  nicht als hier erneut ausgeführt ausgeben.
- Evidenz `evidence/m3-dds-paced-sensors-2026-11-05/`: zehn finale Source-Inventare
  passen (143 Dateien), installierte Python-Dateien bytegleich, unveränderte
  Bridge-/Simulator-Binaries und Native-Probe-Build-/Sourcehashes geprüft.
  Erster Smoke vor strenger Konkurrenzprüfung separat unter development erhalten.
  Roh-PCAPs/Journale lokal, bereinigte Resultate/Hashes/Provider-QoS gespeichert.
  Async-Fences frieren Publish-Aufrufe ein; Restdaten bleiben durch bestehende
  Quieszenz-/Sequenzprüfungen beobachtet, kein behaupteter physischer Wire-Flush.

**Weiter:** getunte DDS-Pacing-/Reconciliation-Semantik und Kosten gegenüber SRT
angleichen; DDS-Emissionsstufen, Clock-/Crypto-/CPU-/Wire-Fenster und volle Matrix
qualifizieren. System-N5-Discovery und Context-wechselnde Unsicherheit bleiben
explizit offen. M3 in Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: gemeinsame Endpoint-Messfenster

- Beide Runner nutzen gemeinsamen Linux-Prozessbaum-Sampler, nominal 250 ms,
  inklusive Observer/Sampler. Gleiche Source-enabled- und Resume-through-drain-
  Phasen, ohne Startup/Shutdown. Innere/äußere CPU-Tickdeltas ohne Interpolation;
  RSS-Summe nur beobachtet, mögliche Shared-Page-Doppelzählung, kein PSS/Peak.
  Fehler/Identitätswechsel/Regression/reaped-child-CPU/Lücken verwerfen CPU.
  Ungesehene kurzlebige Kinder nicht abgedeckt. Alte SRT-Ressourcen bleiben
  Whole-run mit altem Scope und dürfen nicht direkt damit verglichen werden.
- Konditionale PCAP-Zeitfenster: gemeinsame Realtime/Monotonic-Hülle beider Enden,
  <=1000 ppm, keine versteckten Steps, <=1-s-Kalibrierlücken, <=1-ms-Read/Steps.
  Inside/Boundary/Outside inklusive Timestamp-Quantisierung. Keine Fensterbytes
  bei verworfener Kalibrierung; Whole-capture-Gates bleiben davor erforderlich.
- 44 Python-Tests und Demo-Install bestanden. Fünf finale Live-Entwicklungsläufe:
  SRT N0 30 s, DDS system N0 30 s, DDS paced N0 30 s, paced N5 60 s/30 bestätigte
  Commands, sensor-only system N0 15 s. Alle funktional bestanden und alle CPU-
  Fenster beider Enden qualifiziert. Alle Wire-Mappings wegen beobachteter Drift
  über 1000 ppm verworfen, daher keine qualifizierten Wire-Fensterresultate.
  Modell nicht lockern. Ursache noch nicht diagnostiziert.
- Vier alte SRT/DDS-Whole-captures neu ausgewertet: alle bisherigen Felder exakt
  identisch. Fünf Source-Inventare je 146 Dateien aktuell; installierte Scripts
  bytegleich. 56 kompilierte Quelldateien unverändert, Command-/Simulator-Binaries
  identisch zur historischen 02d40e6-Evidenz. Keine neuen ROS-GTest-/M2-Claims.
- Evidenz: `evidence/m3-window-measurement-2026-11-06/`, inklusive Raw-Hashes,
  Prozess-/Clock-Samples, Drift-Verwerfungen und Messscope. Zwei frühere Smokes
  nur Development, vor strengerem Clock-Modell. PCAPs/Journale bleiben lokal.

**Nächster Schritt:** Clock-Mapping ohne Modell-Lockerung qualifizieren; danach
kontrollierte CPU-/Wire-Kosten und getunte DDS-/SRT-Semantik vergleichen. Volle
Matrix/Emission-Stages/Crypto/Cross-session-Unsicherheit bleiben offen. M3 in
Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: Clock-Diagnose und unabhängige Kalibrierung

- Neue standalone Read-only-Probe `tools/clock_probe/main.cpp` plus
  `tools/m3_clock_probe.py`: Python, libc und direkte clock_gettime-Syscalls,
  RAW/BOOTTIME-Diagnose und adjtimex(modes=0). 95 s/910 Samples in network-none-
  Container mit cap-drop ALL. Native Realtime-Offsets ändern sich mindestens
  108/137 us über ca. 107/100 ms; RAW/BOOTTIME ohne Modellverletzung. Python sieht
  die zweite Änderung. Exit 2 ist korrektes negatives Diagnoseresultat.
  TIME_ERROR/STA_UNSYNC (5/64), freq/offset 0. Verursachender Agent nicht belegt;
  kein Nachweis eines Kernel-Bugs, alle Aufrufe im emulierten Linux-Kontext.
- 250-ms-Prozess-Sampling kann kurze Steps übersehen. Dedizierte Clock-Dateien
  nun unabhängig bei Scenario-Polls, mindestens 25 ms Abstand, maximal erlaubte
  Lücke 100 ms. CPU/RSS-Scans unverändert nominal 250 ms. Beide aktuellen Runner
  verlangen Clock-Dateien ohne stillen Legacy-Fallback. Historische Reanalyse
  bleibt als legacy-process-clock gekennzeichnet. 1000-ppm-Modell unverändert;
  auch feinere endliche Samples beweisen keine Abwesenheit versteckter Steps.
- 51 Python-Tests und Demo-Install bestanden. Neue Regression zeigt synthetischen
  150-us-Step: grobe Serie akzeptiert, feinere Serie verwirft. Zusätzlich echter
  finaler SRT-N0-Lauf zeigt in beiden Phasen/beiden Enden grobe Akzeptanz gegen
  dedizierte Drift-Verwerfung. Alte Entwicklungs-Smokes nicht als qualifizierte
  aktuelle Wire-Kosten ausgeben. Native Probe-Verwerfung lag vor dem ersten
  Development-SRT-Sourcefenster, kein behauptetes überlappendes Gegenbeispiel.
- Finale Live-Läufe: SRT N0 30 s/15 bestätigt, DDS system N0 30 s/15 bestätigt,
  DDS paced N5 60 s/30 bestätigt. Alle funktional bestanden, CPU-Fenster beider
  Enden qualifiziert, Wire-Fenster sämtlich verworfen. 149 Source-Dateien je
  Manifest passen; installierte Python-Dateien bytegleich; 56 Produktions-
  Quelldateien und Command-/Simulator-Binaries unverändert. Keine neue ROS-GTest-
  oder volle M2-Ausführung. Drei vorherige Development-Reruns separat erhalten.
- Evidenz `evidence/m3-clock-diagnosis-2026-11-06/`: Probe-Samples/Provenienz,
  dedizierte/Legacy-Kalibrierungen, Clock-/Prozess-Samples und Raw-Hashes.
  Historische Evidenz unverändert, PCAPs/Journale weiter lokal.

**Weiter:** stabile geeignete Linux-Clock-Umgebung oder verifizierte monotone
Packet-Timestamp-Erfassung entwickeln, ohne Driftmodell/Unsicherheit zu lockern.
Danach kontrollierte CPU-/Wire-Kosten und getunte DDS-/SRT-Semantik vergleichen.
M3 bleibt in Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: optionaler Kernel-Monotonic-Packet-Observer

- `--monotonic-capture` in SRT-/DDS-Runner: eigener passiver AF_PACKET-Socketfilter
  mit bpf_ktime_get_ns, skb-Länge, Interface/Richtung und 128-Byte-Prefix. Keine
  Realtime-Konvertierung. Gemeinsame vorhandene Source-/Fenced-Phasen [start,end).
  Eigene Ergebnisse `monotonic_captures`; Realtime-PCAP-Gates unverändert.
- Standalone g++/libbpf-Tool erzeugt verifiergeprüfte BPF-Instruktionen direkt,
  ohne clang/BTF/neues Image. CAP_BPF nur auf eigenen Opt-in-Endpunkten;
  Default-Caps unverändert. Kein Host-/Privileged-/tc-/XDP-/Clock-Eingriff.
  Zero Time-Namespace-Offsets zwingend; vorhandener gemeinsamer Boot-/Clock-Proof.
- 16-MiB-Ring, Datei unter 128 MiB, atomare Seen-/Submitted-/Reserve-/Copy-Zähler,
  Socket-Close/Drain/stabile Footer-Zähler plus Coverage-/Records-Gates.
  Fehler verwerfen Resultate. Präfixparser IPv4 UDP, DDS-IPv4-Fragmente getrennt;
  bekannte IPv6-Nicht-UDP-Ketten begrenzt prüfen/ignorieren, IPv6-UDP/unsupported
  verwerfen. Kein behaupteter physischer Wire-/Delivery-/Population-Nachweis.
  Kernel-Observer-Arbeit kann Endpoint-CPU belastet werden; Messvariante explizit.
- 58 Python-Tests bestanden. Isoliert 40 Datagramme/80 Loopback-Observations:
  Längen stimmen, sämtliche Kernelstamps innerhalb Userspace-Send/Receive-
  Monotonic-Brackets. Gezielter 4-KiB-Overflow: 2.000 Seen, 25 Submitted,
  1.975 Reserve-Fehler, erwarteter Exit 2/Analyzer-Reject. Ohne CAP_BPF kein Ready.
- Vier finale Source-153-Dateien-Inventare passen: SRT N0 Smoke15s/8 bestätigt,
  DDS N0 Smoke15s/8 bestätigt, paced N5 30s/15 bestätigt, Default-Sensor Smoke15s
  ohne Observer/BPF-Cap. Alle funktional bestanden; alle Opt-in-Phasen beider
  Enden CPU-/Monotonic-Capture-qualifiziert, kein Recorderverlust. Installierte
  Scripts bytegleich; 56 Produktionsquellen und Command-/Simulator-Binaries
  unverändert. Keine neue ROS-GTest-/volle-M2-Ausführung.
- Evidenz `evidence/m3-monotonic-capture-2026-11-06/`: Roh-Hashes, native Provenienz,
  Namespace-/Capability-Proofs, Counter/Phasen, synthetische Timestamp-Brackets.
  Frühe IPv6-Parserfehler und längere Development-Runs vor CPU-Scope-Textkorrektur
  separat erhalten. Roh-PCAPs/Prefixes/Journale lokal. Whole-capture-Korroboration
  ist wegen verschiedener Socket-Lebensdauer keine Gleichheits-/Loss-Garantie.

**Weiter:** längere Läufe/Seeds, Observer-Overhead und Tap-/Offload-Scope
qualifizieren; danach kontrollierter SRT-/DDS-Kostenvergleich bei angeglichener
Pacing-/Reconciliation-/Age-/Crypto-Semantik. M3 in Arbeit, PR #2 Draft,
Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: Cgroup-Scope und präregistrierte Observer-Studie

- Read-only cgroup-v2-Counter im bestehenden 250-ms-Endpoint-Sampler: Root-/
  Domain-/Self-PID-Prüfung, Namespace-/Device-/Inode-Identität, CPU-/Memory-Limits,
  CPU-Mikrosekunden, charged Memory und Memory-Events. Neue unabhängige
  `container_cgroup`-Phasen neben Prozess-CPU. Capture/Competitor enthalten,
  außerhalb der Gruppe abgerechnete Host-/Kernelarbeit nicht garantiert erfasst.
  Inner/outer beobachtete Deltas ohne Interpolation, keine CPU-Konfidenzintervalle.
  Charged Memory mit Cache/Kernel, kein RSS/PSS/harter Peak. Fehler/Änderungen
  verwerfen Ressourcenqualifikation, Ausführungsgates unverändert.
- `tools/m3_observer_study.py` schreibt Plan/Quellen vor erstem Kind: SRT N0
  off/on/on/off und DDS system N0 on/off/off/on, jeweils viermal 45 s/Seed1701;
  danach paced N5/Monotonic jeweils 300 s für 1701/2903/4211. Sequentiell, frische
  Endpoints, keine Retries/Host-Tuning. Pärchen verlangen passende Konfiguration/
  qualifizierte Counter; negative Differenzen erhalten, Commandcounts/Effects
  getrennt geprüft und Sensorpopulationen gespeichert. Vorhandene Builds als
  explizite Development-Wiederverwendung; normaler separater M3-Build Voraussetzung.
- 68 Python-Tests und Demo-Install bestanden. Alle elf Plan-Läufe ohne Retry
  bestanden. 44 Cgroup-Fenster aus projizierten Original-Brackets exakt nachgerechnet,
  alle 44 engeren Prozess-CPU-Fenster ebenfalls qualifiziert. Sieben Opt-in-Läufe
  mit 28 qualifizierten Monotonic-Endpunkt-/Phasenfenstern, kein Recorderverlust.
  Lokale Throttle-/Memory-Events null; kein Nachweis ungestörter VM-/Ancestor-CPU.
- Drei Fünfminuten-N5-Läufe bestätigen je 150/150 Commands/150 Effekte, insgesamt
  450. Produced/Callbacks: Seed1701 75.032/19.079, Seed2903 75.018/19.236,
  Seed4211 75.031/19.286. 200/50-Hz-Produktion bleibt erhalten; fehlende Callback-
  Population enthält bewusstes Pacing/Replacement und andere Stufen, kein isolierter
  WAN-Loss. Keine N5-Randomloss-/Jitter-Konfiguration: Seeds markieren hier frische
  Wiederholungen. System-N5-Cold-Discovery damit nicht behoben.
- Acht N0-Paarläufe je 23 bestätigt/23 Effekte. CPU-Differenzen haben wechselnde
  Vorzeichen, keine isolierte Observer-Overheadzahl ableiten. Beobachtete Charged-
  Memory-Maxima on-minus-off ca. 19–23 MiB/Endpunkt; kein physischer Footprint.
  Erster SRT-Off-Lauf IMU 198,182 statt ca. 200 Hz, Callbackpopulationen variieren;
  keinen Lauf post hoc zum Glätten verwerfen. Tabellen/alle Paare erhalten.
- Alle 22 geschlossenen Journale quick_check ok, passende IDs/Hashes/Ergebnisse:
  insgesamt 634 SUCCEEDED/Revision-3-Records pro Seite, Generationen lückenlos.
  Read-only-Audit ändert Haupt-DB-Hashes nicht; keine zusätzliche Crash-Fault-Quali.
- Evidenz `evidence/m3-observer-study-2026-11-06/`: Plan/Studie, projizierte
  Cgroup-Samples, vollständige Run-Manifeste, Scope-/Capability-/Namespace-Proofs,
  Raw-Hashes und Journal-Audits. Initialer Cgroup-Smoke nur Development. Elf
  Inventare je 156 aktuelle Source-Dateien, installierte Scripts bytegleich;
  56 Produktionsquellen und Command-/Simulator-/Native-Capture-Binaries unverändert.
  Keine neuen ROS-GTests/volle M2 behaupten; Roh-PCAPs/Prefixes/Journale lokal.

**Weiter:** kontrollierte/geeignete Ressourcen-Umgebung und Tap-/Offload-Scope
qualifizieren; längere SRT-/DDS-Läufe/weitere Impairment-Profile, volle Matrix und
N3-/N4-Spezialgates. Pacing/Reconciliation/Age/Crypto-Semantik bleibt vor einem
Transportkostenvergleich anzugleichen. M3 in Arbeit, PR #2 Draft,
Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: Tap-/Offload-Probes und Capture-Artefakt v2

- Kontrollierte synthetische UDP-Probes mit frischen eigenen Endpoint-Paaren:
  normales UDP, 100% Egress-netem-Drop, 200-ms-Delay, gezielter Ingress-Drop,
  UDP_SEGMENT ohne/mit netem und shaping-only 512 kbit/s. Kein ROS/SRT-App-Peer,
  kein Konkurrent im Shaping-Probe; kein voller N5-Nachweis dadurch. Je Probe
  positives Restoration-Control im selben offenen Observer zwingend.
- Laufzeitbeleg: 16 normale Datagramme an beiden Taps/Empfänger. Egress-Drop:
  16 gezielte UDP-Matches vor Root, null Tap-/App-Beobachtungen; globale Rootdrops
  enthalten zusätzliche, nicht nach Protokoll zugeordnete Inkremente. Delay: Sender-Tap inklusive Queue-Delay,
  finale Spanne 200,02–206,94 ms (Klassifikationsschwelle 150 ms, kein Präzisionsbound).
  Ingress-Drop: 16 an beiden Taps, 16 gezielte Drops, null App-Receipts.
  Historisches generisches `egress is pre-qdisc`-Label war für dieses Fixture
  falsch. Neue Scope-Texte neutral, alte Artefakte unverändert mit Korrektur lesen.
- UDP_SEGMENT in beiden Fällen: eine 9.642-Byte-SKB-Observation pro Seite,
  gso_segs=8/gso_size=1200, acht 1.200-Byte-Datagramme an der App. Keine physische
  Frame-/Datagrammzählung aus SKB-Anzahl ableiten. Native Capture-Artefakt v2 mit
  168-Byte-Records/GSO-/VLAN-/MTU-Metadaten, 128-Byte-Prefix bleibt. Reader unterstützt
  v1/152 Byte mit unbekannten Offloads; neue Runner verlangen v2. SDK-Wire/IPC
  unverändert. Eigenständige GET-only-Ethtool-Probe speichert Feature-/MTU-Vorher/
  Nachher, kein SET/keine neuen Privilegien; aktive Features allein beweisen Nutzung
  nicht. `frame_interpretation` unabhängig von gültiger SKB-Observation und weiter
  kein Physical-/Checksum-/Padding-/FCS-/Delivery-Nachweis.
- Capture-Datengap entdeckt: Buffered-PCAP schrieb 16 statt 17 bekannter Beobachtungen,
  letztes Control fehlte. Runner jetzt Immediate-Mode, Client zuerst stoppen,
  kurze Inflight-Drainphase. Captured/File/Kerneldrop-Gates strikt. Filtercounter
  können auch bei exakt passenden bekannten Tap-Populationen abweichen; Ursache/
  Einheit nicht vollständig geklärt. Daher separates Population-Reconciliation-Flag,
  keine falsche universelle Gleichheitsinvariante. Unreconciled verwirft Realtime-
  PCAP-Fenster, nicht unabhängige native Observer-Counter. Bekannte-Probe-Tupel in
  finalen Fällen zwischen Native/PCAP exakt identisch.
- 74 Python-Tests bestanden, native Builds mit -Werror. V2-Loopback 40 Datagramme/
  80 korrekte Stamps/Längen; forcierter 4-KiB-Overflow 2.000 Seen/23 Stored/
  1.977 Reserve-Fehler, erwarteter Exit 2. Sieben kontrollierte Fälle bestanden.
  Vier finale Live-Läufe: SRT/DDS N0 Smoke je 8 bestätigt, paced N5 30s/15 bestätigt,
  Default-Sensor Smoke ohne BPF-Observer. Alle Opt-in-Phasen qualifiziert, keine
  Recorderfehler/GSO/VLAN/Over-MTU-SKBs in gemessener UDP-Population; PCAP-Counter
  hier reconciled. Feature-Snapshots stimmen. 159 aktuelle Quellen in Probe und
  vier Manifesten; installierte Python-Dateien bytegleich, 56 Produktionsquellen
  und Command-/Simulator-Binaries unverändert. Native Observer/Feature-Binaries neu.
- Vier alte Classic-Captures numerisch/Klassen unverändert (nur Scope korrigiert),
  vier v1-Endpunkt-/Phasenfenster identisch mit Offload-Metadaten unbekannt/
  Frameinterpretation unqualifiziert. Rohdaten/alte Evidenz nicht umschreiben.
  Neue Evidenz `evidence/m3-tap-offload-2026-11-06/` mit Feature-/Flow-/TC-Proofs,
  Counter-Gegenbeispielen und separaten Development-Iterationen. Volle Docker-
  Inspect-Logs nicht publiziert, nur Capability-/Namespace-Projektion. Roh-PCAPs/
  Prefixes lokal mit Hashes. Keine neuen ROS-GTests/volle M2-Ausführung behaupten.

**Weiter:** V2-/Immediate-Observer-Kosten neu qualifizieren; die vorige V1-/Buffered-
Studie gilt dafür nicht direkt. Weitere Device-/Offload-Pfade, kontrollierte
Ressourcen, verbleibende Profile/Dauern und N3-/N4-Gates. Pacing/Reconciliation/
Age/Crypto vor Transportkostenvergleich angleichen. M3 in Arbeit, PR #2 Draft,
Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: V2-Observer und kurze N1/N2-Probes

- Erste V2-/Immediate-Studie am achten N0-Lauf wegen echter PCAP-Kerneldrops
  (315 Robot/322 Operator) gestoppt. Commands/Effekte und Native Recorder dort
  bestanden. Fehlgeschlagener Plan und acht Manifeste separat archiviert;
  kein Ersatzlauf im alten Plan, keine Lockerung des Zero-Drop-Gates.
- Read-only setsockopt-Diagnose: libpcap 1.10.4 Immediate/TPACKET_V2 mit aktiven
  Offloads und voller Snapshot-Länge hat beim 4.096-KiB-Request nur 64 Slots,
  8 MiB tatsächlich alloziert. Neuer gemeinsamer 32.768-KiB-Request: 512 Slots,
  64 MiB alloziert. Kontrollierter Reader-Stopp bei 400 Datagrammen: alt 336
  Drops je Seite; neu alle 400 plus Recovery-Control, null Drops. Native/App
  vollständig. Kein Offload-SET, kein Preload in normalen Läufen. Ein früher
  OS-Signalnummern-Fehlversuch bleibt ausgeschlossenes Development.
- Neuer eingefrorener Plan: acht N0-On/Off-Läufe je 45 s, vier SRT/DDS-N1/N2-
  Probes je 60 s/Seed 1701, kein langes N5 in diesem Plan. Alle zwölf bestanden,
  PCAP-Kerneldrops null, Native Reserve-/Copy-Verluste null. 299 SUCCEEDED/
  Effekte, keine unaufgelösten Intents; 24 geschlossene Journale integral und
  terminal identisch. DDS N2: 25 statt 30 Versuche, fünf übersprungene Slots;
  max. Invocation-bis-Terminalbeobachtung 10.870,99 ms, kein Execution-Latency-
  Nachweis. Keine TTL-/Lease-/Admission-/Replay-Änderung.
- Studie bindet Immediate/Buffer/Snapshot/V2/Boot-ID sowie acht ausgewählte
  installierte Binär-/SDK-Hashes. 159 Quellen je Manifest gleich, installierte
  Python-Scripts bytegleich, 56 Produktionsquellen und Command-/Simulator-
  Binaries unverändert. 75 Host-Python-Tests bestanden; 48 Cgroup-Phasen aus
  archivierten Projektionen exakt reproduziert. CPU-Differenzen mit wechselndem
  Vorzeichen: keine isolierte Overhead-Schätzung. Charged-Memory-Maxima On-minus-
  Off ca. 20,56–24,19 MiB, kein RSS/PSS oder physischer Footprint.
- Evidenz: `evidence/m3-v2-observer-impairments-2026-11-06/` inklusive fehlgeschlagener
  Studie, Ring-Diagnose, Manifeste, Counter-Projektionen, Hashes und Journal-Audits.
  Roh-PCAPs/Prefixes/Journale bleiben lokal; keine vollständigen Inspect-/Env-Dumps.
  Keine neuen ROS-GTests/volle M2-Ausführung behaupten.

**Weiter:** volle N1/N2-Dauern und drei Seeds, V2/langes N5, kontrollierte Ressourcen,
weitere Device-/Offload-Pfade und N3-/N4-Spezialgates. DDS N2 zeigt weiter große
Terminalbeobachtungs-Latenz trotz erfolgreicher Effekte; nicht als Echtzeitgarantie
lesen. Pacing/Reconciliation/Age/Crypto vor Transportkostenvergleich angleichen.
M3 in Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: DDS-Status-Timeline und begrenzte Poll-Historie

- Historischen N2-Intent 15 korreliert: Receiver-Finish-Zeitstempel 83,47 ms nach
  Aufruf, danach 10.655,11 ms bis Sender-Resultbeobachtung und weitere 132,41 ms
  bis Driver. Zeitstempel vor Journal-Mutation/Commit, kein fsync-/Handlerstart-
  Nachweis. Empfangene SUCCEEDED-STATUS am Tap schon nach 157,52 ms; vorherige
  Control-Sequenz 55 erstmals nach 10.735,75 ms. 51 Stale-Control-Rejections im
  Sender. Reliable-Ordering/Retransmission-Blockade mit anschließender Freshness-
  Ablehnung ist damit konsistent, aber keine per-Frame-Callback-Ursache bewiesen.
- Offline Generated-CDR-Fingerprint-Probe: 516 gegen Journale validierte
  Beobachtungen, je eindeutiger Native-Längen-/128-Byte-Prefix-Match. Kein
  generischer RTPS-Parser/Reassembler/Population-Vollständigkeitsnachweis;
  Serialisierungs-Roundtrip-Differenzoffsets explizit, keine volle Bytegleichheit
  behaupten. Native-Monotonic-Stamps, keine PCAP-Realtime-Konvertierung. Rohdaten
  lokal, Decoder-/Image-/Generated-Type-Provenienz und Hashes archiviert.
- DDS-Driver speichert erste 32/letzte 32 Status-Service-Polls je Intent, Zähler
  für ausgelassene Mitte. Keine Terminalerfindung aus Budgetablauf/NOT_FOUND.
  Neue Read-only-Timeline unter tools/m3_dds_result_timeline.py verlangt geschlossene
  checkpointed Journale, Common-VM/Zero-Offsets, Hash-/Kontext-Konsistenz und
  passende aktuelle Owner. Unknown/fehlende/recovered Records ohne Zerlegung.
- Drei eingefrorene neue N2-System-DDS-Läufe je 60 s/Seeds 1701, 2903, 4211:
  84 Versuche, 82 SUCCEEDED/Effekte, zwei Receiver-EXPIRED Revision 1 ohne Dispatch,
  keine unaufgelösten Intents. Pro Seed Erfolg/Expiry/Skipped: 27/1/2, 30/0/0,
  25/1/4. Max. Terminalbeobachtung 5.413/1.448/8.459 ms. Beide Expiries mit einem
  Stale-COMMAND am Receiver; Poll-Historien vollständig (27/42), spätere neue IDs
  erfolgreich. Kein generationsändernder Effekt für die Expiries.
- PCAP-Kerneldrops und Native Reserve-/Copy-Verluste null; sechs Journale integral
  und terminal identisch. 161 Quellen während aller drei Läufe unverändert,
  acht installierte Binär-/SDK-Hashes sowie installierte Python-Scripts konstant.
  Danach nur Offline-Analyzer/Test um Current-Owner-Guard ergänzt: eingefrorene
  Versionen erhalten, finale Reanalyse aller Timelines identisch. 56 Produktions-
  C++/Header/Proto-Quellen unverändert, keine neuen ROS-GTests/volle M2-Ausführung.
  Demo-Python-Paket normal installiert, 83 finale Host-Python-Tests bestanden.
- Evidenz: evidence/m3-dds-status-timeline-2026-11-06/ mit Histories, getrennten
  Success-/Expiry-Ergebnissen, Source-/Owner-Guard-Provenienz und Raw-Hashes.
  Keine vollständigen Inspect-/Env-Dumps. Deadline/Lease/Freshness/QoS/SDK/Wire/
  IPC/Atomic-Start/Sealing/No-Replay unverändert, Intrinsic/M4 unverändert.

**Weiter:** volle 600-s-N1/N2-Matrix mit drei Seeds, V2/langes N5 und kontrollierte
Ressourcen, andere Device-/Offload-Pfade sowie N3-/N4-Spezialgates. Lange STATUS-
Beobachtung und andere SRT-/DDS-Semantik/Security verhindern Transportkosten- oder
Echtzeit-Überlegenheitsbehauptungen. M3 in Arbeit, PR #2 bleibt Draft.

## Fortsetzung 2026-11-06: Default DDS N2 je 600 s/drei Seeds

- Eingefrorener Plan vor erstem Lauf: System-DDS, N2, Seeds 1701/2903/4211,
  je 600 s, frische sequentielle eigene Container, Native Observer v2 aktiv,
  Immediate/Full-Snapshot/32.768-KiB-PCAP-Request. Keine Retries/Ersatzläufe,
  kein Rebuild/Policy-Wechsel. Netem-Readbacks und konkrete TC-Argumente erhalten.
- Alle drei Source-Fenster vollständig (600,141/600,126/600,138 s), Execution- und
  Capture-Gates bestanden. Pro Seed Versuche/Erfolge/Effekte/Expiry/Not-admitted/
  Skipped: 282/277/277/5/0/18, 285/281/281/4/0/15, 276/272/272/3/1/24.
  Insgesamt 843 Versuche, 830 SUCCEEDED/Effekte, zwölf Receiver-EXPIRED Revision 1
  ohne Dispatch, ein BUSY vor Queue-Aufnahme, 57 übersprungene Slots. Keine
  UNKNOWN/unaufgelösten Intents, keine automatischen Wiederholungen.
- Seed 4211 Intent 268: Submission BUSY=1, kein Journal-Record an beiden Seiten,
  Sender überträgt nur 275 der 276 Versuche. Explizite Admission-Antwort und
  Abwesenheit getrennt halten; aus generischem NOT_FOUND keine Nichtausführung
  ableiten. Späterer neuer Intent behält erwartete Generation. Sechs Journale
  integral/terminal identisch; Generation-Chains ergeben 277/281/272. Dispatches
  und atomare Startclaims entsprechen Effekten; zwölf Expiries erhöhen Generation
  nicht. Max. Terminalbeobachtung je Seed 8.463,640/5.610,490/5.895,465 ms.
- Sensor-Altersqualifikation: Seed 1701 **fehlgeschlagen** (sechs Clock-Steps,
  max. 6,206431 ms, max. Offset-Abweichung 9,055105 ms). 25.435 IMU-/13.445 Joint-
  Callbacks clock-rejected. Histogramme nicht als qualifizierte Gesamtverteilung
  lesen. Seeds 2903/4211 Shared-VM-Age-Estimates qualifiziert; trotzdem sämtliche
  Realtime-PCAP-Fenster wegen strengerem Clockmodell unterdrückt. Native Kernel-
  Monotonic-Counter separat qualifiziert, kein Physical-/Delivery-Nachweis.
- Alle PCAP-Kerneldrops/native Reserve-/Copy-Verluste null, zwölf Cgroup-Phasen
  aus archivierten Projektionen exakt reproduziert. 161 Sources in drei Manifesten
  und acht installierte Binär-/SDK-Hashes sowie installierte Python-Bytes konstant.
  Seed 2903 Robot-PCAP zusätzlich Filterpopulation unreconciled: 170.340 gefiltert
  vs. 170.338 Captured/File, null Kerneldrops; keine Ursache/Vollständigkeit daraus
  ableiten. Realtime-Fenster ohnehin unterdrückt, Native-Gates separat.
  56 Produktions-C++/Header/Proto-Quellen unverändert seit eb46aba. Ein gemeinsamer
  VM-Boot in dieser Kohorte. Vorige 83 Host-Python-Tests unverändert; keine neuen
  ROS-GTests/volle M2-Ausführung behaupten. Diese Fortsetzung ändert keine Runtime-
  Quellen, nur Evidenz/Planungsdokumentation. Intrinsic/M4 unverändert.
- Evidenz: evidence/m3-dds-n2-full-2026-11-06/ mit Plan, drei Manifesten, per-State-
  Latenzen, Admission-/Generationsbelegen, Clock-/Sensorpopulationen, Journal-Audits,
  Raw-Hashes und Cgroup-Projektionen. Keine vollen Inspect-/Env-Dumps; Roh-PCAPs,
  Prefixes, Journale und Clocks lokal. Keine kausale Ressourcen-/Transportüberlegenheit.

**Weiter:** DDS-N2-Dauer/Seed-Ausführung erledigt, **N2-Altersgate weiter offen**.
Volle SRT-N2- und beide N1-Matrizen, V2/langes N5, deterministisches N3, N4-Phasen,
andere Devices/Offloads, kontrollierte Ressourcen und Semantik-/Security-Parität.
M3 in Arbeit, PR #2 bleibt Draft; keine Echtzeit-/Lossless-/Hardwarefreigabe.

## Fortsetzung 2026-11-06: SRT N2 je 600 s/drei Seeds

- Eingefrorener Plan vor erstem Lauf: SRT N2, Seeds 1701/2903/4211, je 600 s,
  frische sequentielle eigene Endpoint-Paare. Bestehende Crypto-/Profile-/Deadline-/
  Lease-/Journal-/Atomic-Start-/No-Replay-Policy, Native v2 und Immediate/Full-
  Snapshot/32.768-KiB-PCAP unverändert. Keine Rebuilds, Retries oder Ersatzläufe.
- Alle drei vollständigen Source-Fenster (600,149477/600,101959/600,140695 s)
  bestanden. Je Seed 300 SUCCEEDED/Effekte, insgesamt 900; null EXPIRED/FAILED/
  REJECTED/UNKNOWN/unaufgelöste/not-admitted/übersprungene Intents. Max. lokale
  Invocation-bis-Terminalbeobachtung 1.106,214/1.309,764/1.110,049 ms; keine
  Ausführungs-/Netzlaufzeitgrenze daraus ableiten. Sechs geschlossene Journale
  integral, je Intent an beiden Seiten Revision 3/Result/Hash/Generation identisch.
  Generation-Chains und Device-Effekte je 300, keine neue Intent-Wiederholung.
- Alle sechs Conservation-Residuals je Source-Fenster null und exakt nachgerechnet.
  Produced/Published/Observer je Seed: 150.036/64.233/64.176,
  150.026/64.037/63.980, 150.036/64.183/64.125. Sämtliche lokalen Verlust-/Replace-/
  Reject-Populationen behalten; Accept-to-Receiver-Gap nicht als isolierter WAN-
  Verlust oder FEC-Nutzen auslegen. Nicht alle produzierten Samples werden zugestellt.
- Source-fenced Publication-Age-Upper-Maxima (auf 1 ms aufgerundet) IMU/Joints:
  143/168, 144/164, 141/163 ms; unter unverändertem 250-ms-Gate. Origin ist Bridge-
  Ingress, kein physisches Sampling-to-Delivery und keine DDS-Header-Age-Parität.
  Diagnostics-Hold-Dauern enthalten Startup/Tails/Gaps, keine exakte Window-Uptime.
- PCAP-Kerneldrops und Native Reserve-/Copy-Verluste null. Sechs PCAP-Populationen
  hier reconciled, kein universeller Completeness-/Physical-Delivery-Nachweis.
  Alle Realtime-PCAP-Fenster wegen Clock-Qualifikation unterdrückt; Native-Monotonic
  separat qualifiziert. Zwölf Cgroup-Phasen aus archivierten Projektionen exakt
  reproduziert. 161 Quellen und acht ausgewählte installierte Binär-/SDK-Hashes
  sowie installierte Python-Bytes konstant; 56 Produktionsquellen unverändert seit
  fd23de6. Ein VM-Boot in der Kohorte. Keine Runtime-Quelländerung; vorherige 83
  Host-Python-Tests unverändert, keine neuen ROS-GTests/volle M2-Ausführung behaupten.
- Evidenz: evidence/m3-srt-n2-full-2026-11-06/ mit Plan, Manifesten, Journal-/Generation-
  Belegen, Source-/Age-/Loss-Tabellen, PCAP-Populationen, Cgroup-Projektionen und
  Raw-Hashes. Roh-PCAPs/Prefixes/Journale/Clocks lokal; keine vollen Inspect-/Env-Dumps.
  Intrinsic/M4 unverändert. Kein kontrollierter Ressourcen-/Transportvorteil behauptet.

**Weiter:** volle N2-Dauer/Seed-Ausführung für SRT und System-DDS dokumentiert;
DDS-N2-Altersgate und Realtime-PCAP-Clockqualifikation bleiben offen. Volle N1-
Matrizen, V2/langes N5, deterministisches N3, N4-Command-Phasen, andere Devices/
Offloads, kontrollierte Ressourcen und Age-/Pacing-/Reconciliation-/Security-Parität.
M3 in Arbeit, PR #2 bleibt Draft.

## Fortsetzung 2026-11-06: Capture-Retention und SRT N1 je 600 s/drei Seeds

- Vor erster N1-Ausführung Retention-Preflight: SRT N2 hatte je Endpoint
  125.447.816..125.572.581 Byte bei nominell 128.000.000 Byte rotierender Kapazität.
  Normale SRT-/DDS-M3-Runner nutzen nun gemeinsam 16 statt 8 Dateien à 16 MB,
  nominell 256.000.000 Byte. Rotation (Dateigröße/Anzahl/nominelle Bytes) im Manifest
  und Vergleichsguard gebunden. Kein fehlgeschlagener N1-Lauf/Retry versteckt;
  Kernelbuffer/Immediate/Snapshot/Offloads/Gates unverändert. Kein unbegrenzter
  Volumennachweis; Tcpdump-Dateischwellen können um einen Record überschritten werden.
- Separater UDP-Volumenprobe mit 1-MB-Schwellen: zwei Dateien behalten je Seite
  1.206 von 2.001 bekannten Records, obwohl Footer 2.001 captured/null Kerneldrops
  meldet. Bestehendes Captured/File-Gate lehnt korrekt ab. Vier Dateien behalten
  alle 2.001 mit exakter Native-ID-/Längen-Gleichheit, null Drops; App in beiden
  Fällen vollständig und Recovery-Control vorhanden. Kein Kernelverlust daraus
  ableiten; kontrollierter Capture-Mechanismus-Test, keine Transportabnahme.
- Eingefrorener SRT-N1-Plan: Seeds 1701/2903/4211 je 600 s, frische sequentielle
  Endpunkte, keine Rebuilds/Retries/Ersatzläufe/Policy-Änderungen. Alle drei Source-
  Fenster vollständig (600,093151/600,153512/600,141223 s). Je 300 SUCCEEDED/Effekte,
  insgesamt 900; null Expired/Failed/Rejected/UNKNOWN/unaufgelöste/not-admitted/
  übersprungene Intents. Max. lokale Terminalbeobachtung 923,544/264,239/467,177 ms.
  Keine Ausführungs-/Netzlaufzeitgrenze daraus ableiten.
- Sechs Journale integral/terminal identisch, Revision 3/Hash/Result/Generation
  pro Intent passend; Device-Generationen/Effekte je 300. Drei Source-Zusammenfassungen
  exakt reproduziert, alle sechs Conservation-Residuals je Fenster null. Produced/
  Published/Observer je Seed: 149.484/110.267/110.064, 150.038/111.112/111.047,
  150.036/111.381/111.300. Erste IMU-Quellrate 199,107 Hz, andere ca. 200 Hz;
  Ratenvariation/Verluste behalten, nicht normalisieren oder als WAN-Loss/FEC-Nutzen
  isoliert auslegen. Nicht alle produzierten Samples werden zugestellt.
- Source-fenced Publication-Age-Upper-Maxima IMU/Joints: 87/119, 63/83, 63/85 ms,
  unter unverändertem 250-ms-Gate. Origin Bridge-Ingress, keine DDS-Header-/Physical-
  Sensor-Age-Parität. PCAP-Kerneldrops und Native Reserve-/Copy-Verluste null;
  sechs PCAP-Populationen reconciled, kein universeller Completeness-Nachweis.
  Alle Realtime-PCAP-Fenster wegen Clock-Qualifikation unterdrückt, Native separat.
  Zwölf Cgroup-Phasen aus Projektionen exakt reproduziert.
- 161 Quellen während drei Läufen konstant; gegenüber d2912fc nur Capture-Helper,
  zwei Haupt-Runner und ein Guard-Test geändert. Acht installierte Binär-/SDK-
  Hashes und installierte Python-Bytes konstant; 56 Produktions-C++/Header/Proto-
  Quellen unverändert. 83 Host-Python-Tests bestanden, Retention-Mischkonfiguration
  negativ abgedeckt. Keine neuen ROS-GTests/volle M2-Ausführung behaupten.
  Keine SDK-/Wire-/IPC-/Deadline-/Lease-/Atomic-Start-/Replay-Policy-Änderung.
- Evidenz: evidence/m3-srt-n1-full-2026-11-06/ mit separatem Retention-Preflight/
  Probe, Plan, Manifesten, vollständigen Source-/Loss-/Age- und Terminalpopulationen,
  Journal-/Generationsbelegen, Cgroup-Projektionen und Raw-Hashes. Roh-PCAPs/
  Prefixes/Journale/Clocks lokal; keine vollen Inspect-/Env-Dumps. Intrinsic/M4
  unverändert; keine kausale Ressourcen-/Transportüberlegenheit behauptet.

**Weiter:** volle System-DDS-N1-Matrix; DDS-N2-Altersgate/Realtime-PCAP-Clockqualifikation,
V2/langes N5, deterministisches N3, N4-Command-Phasen, andere Devices/Offloads,
kontrollierte Ressourcen und Age-/Pacing-/Reconciliation-/Security-Parität bleiben
separat offen. SRT N1/N2 und DDS N2 sind als volle Dauer/Seed-Ausführung dokumentiert.
M3 in Arbeit, PR #2 bleibt Draft.

## Fortsetzung 2026-11-06: System-DDS N1 und N1/N2-Ausführungsmatrix

- Eingefrorener Default/System-DDS-N1-Plan: Seeds 1701/2903/4211, je 600 s,
  frische sequentielle eigene Endpunkte, Native v2/Immediate/Full-Snapshot/
  32.768-KiB-Kernelbuffer und 16×16-MB-Retention wie e3c5c70. Keine Rebuilds,
  Runtime-/Policy-/Capture-Änderungen, Retries oder Ersatzläufe.
- Alle drei Source-Fenster vollständig (600,115900/600,118402/600,132039 s).
  Pro Seed Attempts/SUCCEEDED/Effekte/Expired/Skipped: 297/296/296/1/3,
  297/296/296/1/3, 298/298/298/0/2. Insgesamt 892 Versuche, 890 Erfolge/Effekte,
  zwei Receiver-EXPIRED Revision 1 ohne Dispatch und acht übersprungene Slots.
  Keine UNKNOWN/unaufgelösten/not-admitted/rejected/failed Intents. Max. lokale
  Terminalbeobachtung 5.350,575/5.316,245/2.473,593 ms, kein Handler-/Netzlaufzeitbound.
- Sechs geschlossene Journale integral und terminal/immutable identisch, ohne
  fehlende/abweichende Records. Device-Generationen/Effekte 296/296/298; Expiry
  erhöht Generation nicht, spätere neue Intents folgen dem gleichen erwarteten
  Stand. Finale Timelines aus Original-Owner-Journalen exakt reproduziert;
  keine DDS-Timingzerlegung für fehlende/unklare/Recovered-Records erfinden.
- Alter: Seed 1701 **unqualifiziert**, vier beobachtete Clock-Steps, max.
  25,965389 ms und max. Offset-Abweichung 34,616970 ms. 17.809 IMU-/6.403 Joint-
  Callbacks clock-rejected (24.212 gesamt). Seeds 2903/4211 Shared-VM-Age-Estimates
  qualifiziert. Vollständige Histogramme/Clock-Reject-/Missing-Populationen erhalten;
  keine Gesamtaltersgrenze aus günstigem Teilset ableiten. N1-Altersgate bleibt offen.
- Produced/Received je Seed 150.010/112.123, 150.024/112.928, 150.026/111.710;
  Source-Raten und Callback-Defizite separat halten, kein isolierter WAN-Loss oder
  Transportvorteil. Sämtliche Realtime-PCAP-Fenster wegen Clock-Qualifikation
  unterdrückt. Native-Monotonic-Coverage separat qualifiziert. Alle PCAP-Kerneldrops/
  Native Reserve-/Copy-Verluste null, sechs PCAP-Populationen reconciled; kein
  universeller Completeness-/Physical-Delivery-Nachweis. Zwölf Cgroup-Phasen aus
  Projektionen exakt reproduziert.
- 161 Quellen entsprechen während aller Läufe und final e3c5c70. Acht ausgewählte
  installierte Binär-/SDK-Hashes und installierte Python-Bytes konstant; 56
  Produktions-C++/Header/Proto-Quellen unverändert. Ein VM-Boot in dieser Kohorte.
  Vorige 83 Host-Tests unverändert, keine neuen ROS-GTests/volle M2-Ausführung
  behaupten. Diese Fortsetzung ändert nur Evidenz/Planungsdokumentation.
- Evidenz: evidence/m3-dds-n1-full-2026-11-06/ mit Plan, Manifesten, Journal-/Generation-
  Audits, Original-Owner-Timelines, Source-/Age-/Clock-Populationen, Capture-Metadaten,
  Cgroup-Projektionen und Raw-Hashes. Roh-PCAPs/Prefixes/Journale/Clocks lokal;
  keine vollen Inspect-/Env-Dumps. Intrinsic/M4 unverändert.
- execution-matrix.json in dieser Evidenz fasst SRT N1/N2 und System-DDS N1/N2
  zusammen: alle vier Kohorten mit drei Seeds/je mindestens 600 s ausgeführt.
  Nur die Dauer/Seed-Ausführung ist damit abgeschlossen. Capture-Retention,
  Altersorigins/Modelle, Crypto, Pacing und Hostbedingungen unterscheiden sich;
  keine kausale Kosten-/Überlegenheitsbehauptung aus getrennten Kohorten.

**Weiter:** V2/langes N5, deterministisches N3 (DATA/FEC getrennt), N4-Command-Phasen,
DDS-N1/N2-Altersgates und Realtime-PCAP-Clockqualifikation, weitere Devices/Offloads,
kontrollierte Ressourcen und Age-/Pacing-/Reconciliation-/Security-Parität.
N1/N2-Dauer/Seed-Ausführung komplett dokumentiert; M3 weiterhin in Arbeit,
PR #2 Draft. Keine implizite Hardware-/Echtzeit-/Lossless-Freigabe.

## Fortsetzung 2026-11-06: N5 mit aktueller Capture-Konfiguration

- Separate, vor Start eingefrorene paced-DDS-N5-Kohorte: Seeds 1701/2903/4211
  je 300 s, simultaner Start, private frische sequentielle Endpunkte. 512-kbit/s-
  Root-TBF je Richtung, Burst 4096, Limit-Request 32768, Child-Netem-Queue 16;
  kein stochastischer Delay/Loss, Seeds nur Wiederholungslabels. Pinned JSON zeigt
  TBF Rate/Burst/normalisierte Latenz (448000), kein erfundenes Limit-Readback.
- DDS-Kandidat explizit paced-sensors: nur Sensorwriter asynchron/KeepLast(1),
  gemeinsamer 1600-Controller-Bytes/50-ms-Budget, 1200-Byte UDP/SHM. Control unverändert.
  Native Provider-Preflight vor jedem Lab in network-none, dessen Binärhash als
  neunter ausgewählter Hash eingefroren. XML/161 Sources/Install-Scripts konstant.
  Quellen dieser Kohorte entsprechen 1bf9bfe vor dem späteren SRT-Tooling-Patch.
- Alle drei paced-DDS-Läufe bestanden: je 150 SUCCEEDED/Effekte, gesamt 450;
  null Expired/UNKNOWN/unresolved/not-admitted/Skipped. Source/Callback je Seed
  75031/19216, 75027/19073, 75026/19188. Absichtliches Middleware-Pacing und andere
  Stufen nicht als isolierten WAN-Loss deuten. Alle Shared-VM-Age-Estimates
  qualifiziert, alle Realtime-PCAP-Fenster weiterhin unterdrückt. Sechs Journale
  stimmen überein, zwölf Cgroup-Fenster exakt reproduziert. Recorderverluste null.
- Iperf-Whole-Run-Offer ca. 128000,016/128019,300/128002,557 bit/s; Liveness-Polls
  positiv. Intervall/Setup/Total-Projektionen und Raw-Hashes erhalten, keine
  matched-window Delivery-/Loss-Garantie. Default/System-DDS-N5-Discovery bleibt offen.
- SRT-Runner fehlten diese Competitor-Gates. Patch 80c5590 ergänzt Poll-Liveness
  und denselben Offered-Load-Validator. 83 Host-Tests bestanden. Separater Negativtest
  beendet ausschließlich den Client im eigenen Robot-Container nach echtem
  Measurement-Marker: erwartetes failed/competitor-exited beobachtet. Zusätzlicher
  Capture-Analysefehler wegen absichtlich fehlender Endpoint-Fenster; keine positive
  N5-/Capture-/Journal-Abnahme aus diesem unterbrochenen Development-Fall behaupten.
- Danach separater SRT-N5-Plan, Quellen bei 80c5590 eingefroren. Seed 1701 bestanden:
  131 SUCCEEDED/Effekte, 19 Skipped, null unresolved. Seed 2903 **fehlgeschlagen**:
  PCAP-Kerneldrops Robot 2672/Operator 2637. Application-Fenster endet mit 104
  bestätigten Effekten, 105 Versuchen, 45 Skipped und einem offenen Intent 105.
  Seed 4211 wegen Fail-fast nicht ausgeführt, kein Ersatzlauf/Retry/Gate-Waiver.
- Intent 105: Senderjournal UNKNOWN/reconcile-required, Revision 0, ungültiges
  Result; Receiver ohne Eintrag. 104 gemeinsame Erfolgsrecords stimmen überein,
  final beobachtete Generation/Effekte 104. NOT_FOUND/Abwesenheit nicht als
  Nichtausführung/Expiry/Erfolg auslegen. Reconcile-required bleibt
  unsicher, obwohl die Verbindung später wieder ready ist; kein automatischer Replay.
  Begin-/End-Session-IDs und Generationen sind identisch; daraus keinen belegten
  Session-ID-Wechsel oder eindeutige UNKNOWN-Ursache behaupten.
- Native UDP/PCAP-Multiset-Vergleich identifiziert exakt alle 2672/2637 fehlenden
  Records eindeutig in drei späten Zeitclustern; große Cluster ca. 2,7/3,1 s.
  Native Reserve-/Copy-Verluste null und beide Phasen unabhängig qualifiziert.
  Das rettet keine fehlgeschlagene PCAP-/Gesamtabnahme. Sampler-Gaps beweisen keine
  globale Pause; keine eindeutige Scheduler-/Storage-Ursache behaupten. Acht
  Cgroup-Fenster und beide Source-Summaries der ausgeführten SRT-Fälle reproduziert,
  fehlgeschlagenes App-Counter-Result nicht als vollständige Qualifikation verkaufen.
- Evidenz getrennt: evidence/m3-dds-paced-n5-v2-2026-11-06/ und
  evidence/m3-srt-n5-v2-2026-11-06/ inkl. Development-Negativfall, unverändertem
  fehlgeschlagenem Plan, Raw-Hashes, Closed-Journal-Audit und Capture-Gap-Analyse.
  Keine Runtime-C++-/SDK-/Wire-/IPC-/Deadline-/Lease-/Replay-Policy-Änderung,
  keine neuen ROS-GTests/volle M2-Ausführung; Intrinsic/M4 unverändert.

**Weiter:** SRT-N5-Recorderverlust untersuchen/qualifizierbare Aufnahme sicherstellen;
Intent-105-Unsicherheit beibehalten und Kontextwechsel-/Lastverhalten gezielt
qualifizieren. N3 deterministische DATA/FEC-Verluste, N4-Command-Phasen, Default-DDS-
N5-Discovery, bestehende Age-/Realtime-Clock-Gaps und kontrollierte Semantik-/Security-/
Ressourcenparität offen. M3 nicht abgeschlossen, PR #2 bleibt Draft.

## Fortsetzung 2026-11-06: Recorder-/Command-Diagnostik

- Optional `run_m3.py --recorder-diagnostics`: begrenzte 100-ms-/proc-Beobachtungen
  von tcpdump mit PID/Startzeit, State, Scheduler-/Context-Switch-/verfügbaren
  I/O-Zählern und monotonen Read-Brackets. Default aus, 75000-Sample-Grenze;
  fehlende/gesperrte Felder explizit, keine Completeness-/Ursachenbehauptung.
- Network-none/Loopback-Kontrollen: Baseline 2076 Datagrams/Receipts/PCAP-Records,
  null Drops. Bekannte ca. 1,5-s-SIGSTOP-Pause: 2116 Receipts, 1310 PCAP-Records,
  Kernel-Dropzähler 1612, 14 T-State-Samples; Zero-Drop-Gate verwirft und Recovery-
  Marker nach SIGCONT erfasst. Loopback-Filterzähler doppelt, keine Datagramm-/
  Frame-Äquivalenz oder Erklärung des früheren N5-Verlusts ableiten.
- Separates N5-Development bei 013927f, 60 s: beide PCAPs ohne Drops, zwei
  bestätigte Effekte, dritter Intent unresolved/Sender UNKNOWN, Receiver ohne
  Record, 27 Skipped. Harness-passed erlaubt Development-Uncertainty und ist keine
  N5-Command-Abnahme. Unsicherheit damit auch ohne Recorderverlust beobachtet;
  keine eindeutige Transition/Ursache, kein Replay/Expiry/Erfolg erfunden.
- SRT-Driver ab 56b7b8a nutzt bestehenden bounded Status-History-Helper: erste
  32/letzte 32 Polls, Omission-Zähler, State/Reason/Revision/Found und Local-/Peer-
  Errors. Admission/Cadence/Terminalklassifikation unverändert. Separates 30-s-
  N5-Development: 12 Erfolge/Effekte, drei Skipped, null unresolved, null PCAP-Drops;
  86 Statuspolls von LOCAL_QUEUED bis SUCCEEDED erhalten. Kein Ersatz für die
  fehlgeschlagene Frozen-Kohorte oder deren nicht ausgeführten dritten Seed.
- Echte N5-Endpunkte verweigern /proc-I/O-Counter nach tcpdump-Privilege-Drop
  (PermissionError), wchan=0 nicht als verfügbare Waitsite interpretieren. Kein
  zusätzliches Capability/anderer tcpdump-User in N5. Loopback-Kontrolle mit
  explizitem -Z root ist nur eine Diagnosekontrolle, deren I/O-Sicht nicht auf N5
  übertragen. Scheduler/States/Samplegaps verfügbar; ein D-State-Sample beweist
  keine Storage-Ursache. Gegenüber früheren Kohorten zusätzlicher Observer-Workload.
- 88 Host-Python-Tests bestanden; ROS/SRT-Development validiert Adapter. Keine
  neuen ROS-GTests/volle M2-Ausführung; acht ausgewählte installierte Dateien
  nach Läufen unverändert zur früheren N5-Freeze geprüft. Keine Production-C++-,
  SDK-/Wire-/Deadline-/Lease-/Replay-Änderung. Evidenz mit unveränderten Manifesten,
  Sample-Replay, Read-only-Journal-Audits/Raw-Hashes:
  evidence/m3-recorder-diagnostics-2026-11-06/. Rohdaten bleiben lokal.

**Weiter:** Command-Invalidation-/Transport-Handoff-Grenzen gezielt instrumentieren,
Live-/Shutdown-/Recovery-Transitions unterscheidbar machen; Recorderverluste mit
opt-in Beobachtungen korrelieren, falls erneut beobachtet. Original-Intent 105
bleibt unsicher; SRT-N5-Gesamtqualifikation, Default-DDS-N5, N3/N4 und bestehende
Age-/Clock-/Security-/Ressourcengates offen. M3 in Arbeit, PR #2 Draft; M4 unverändert.

## Fortsetzung 2026-11-06: Command-Handoff-Ursache beobachtet und behoben

- 381dfa8 ergänzt opt-in `--command-diagnostics` / ROS-Parameter
  `command_diagnostics`: fester 256-Event-Trace, Producer schreiben mit Try-lock
  ohne Wait/I/O/Callbacks, Loss-Zähler explizit. ROS-Pump drainiert JSON; nach
  Endpoint-Join finale Attempted/Dropped-Bilanz. Events für Coordinator-Invalidation
  (Sessionwechsel vs. Abandoned-Submit), Admission/Handoff, Transportdrops,
  SDK-Acceptance und Lifecycle. Aktuelle und gespeicherte Owner-Epochen bei
  UNKNOWN separat. Kein Wire-/Worker-IPC-Formatwechsel; Default aus.
- Separates vorab fixiertes 90-s-N5-Development (Seed 2903) bei 381dfa8:
  zehn Erfolge/Effekte, ein offener Intent 11, 34 Skipped, null PCAP-Drops.
  Trace: Envelope-Erstellung für 11 verwirft `clock_unqualified` vor SDK-Handoff.
  Letzter Driverpoll bleibt LOCAL_QUEUED; späterer Teardown-Sessionwechsel fordert
  Invalidation an, geschlossenes Journal danach UNKNOWN/reconcile-required.
  Keine nachträgliche Expiry/Erfolg/Nichtausführung oder Replay erfinden.
- Originalmanifest bleibt failed: erster Tracevalidator erwartete fälschlich
  exakt zwei Bridge-Logs. Tatsächlicher Setup-Linkreset erzeugt drei Inkarnationen;
  alle drei Traces integral, 43/4/4 Events, null Drops. Reanalyse getrennt, kein
  Umetikettieren des ursprünglichen Manifests. Validator ab 899a6eb prüft jede
  Inkarnation und beide Rollen, statt die legitime Setup-Inkarnation abzulehnen.
- 899a6eb hält noch nicht ans SDK übergebene Commands bei softem Clock-Ausfall in
  einem reservierten Ingress-Slot. Dieser zählt innerhalb der bestehenden 64/
  56-Grenzen, FIFO bleibt erhalten. Original-Proof/Origin/Deadline unverändert;
  pro Versuch Liveness/Context/Deadline prüfen. Probe-/Socket-Owner laufen weiter.
  Expiry/Revocation/Context-Loss/andere Envelopefehler weiterhin fail closed;
  kein neuer Admit, keine Budgetverlängerung und kein SDK-Command-Replay.
- Kontrollierter nativer Regressionstest mit 150-ms-Probe-Lifetime schlägt mit
  altem Transport erwartungsgemäß fehl (Command discarded statt Clock-Wait).
  Fix auf IPv4/IPv6: Deferred/Ingress-Charge, One-shot-Ticket, genau ein späterer
  SDK-Handoff mit Original-Origin/5000-ms-Budget. Zweites gehaltenes Command wird
  nach Worker-Revocation verworfen und auch nach Clock-Erholung nicht gesendet.
- Separate neue 90-s-N5-Development-Ausführung bei 899a6eb: 32 Erfolge/Effekte,
  13 Skipped, null unresolved/UNKNOWN/PCAP-Drops. Zwei Clock-Deferrals, beide
  Intents erfolgreich; SDK-Accepts 32. Traces 108/4/4 Events, null diagnostische
  Drops; 32 gemeinsame Journalrecords stimmen überein, Generation/Effekte 32.
  Geänderte kompilierte Runtime plus Trace/Recorder-Observer; keine kausale
  Leistungs-/Kostenvergleichsbehauptung und kein Ersatz für frühere Abnahme.
- Finale neue Builds: 68 SDK-/Native-CTests, 36 ROS-reported (32 GTests plus
  Wrapper) und 92 Host-Python-Tests bestanden. Kein neuer voller M2-Acceptance-
  Lauf behauptet. Consumer wegen öffentlicher Config-Layout-Erweiterung neu gebaut.
- Historische Intents 105 und 3: Immutable/read-only Journal-Owner-Checks stimmen
  mit jeweiligem Operator-Checkpoint überein, belegen aber keine eindeutige alte
  Transition. SRT-Checkpointlabels sender/receiver sind Sensor-Richtung; Command-
  Sender ist Operator/Sensor-Receiver. Historische Unsicherheit bleibt erhalten.
- Evidenz: evidence/m3-command-handoff-2026-11-06/ mit unveränderten Manifesten,
  Freeze/Binding, Original-Trace-Logs, Reanalyse, Journal-/Source-/Raw-Hashes,
  Expected-Failure/positiven Tests. Roh-PCAP/Prefixes/Journale/Clocks lokal;
  keine kompletten Inspect-/Env-Dumps/Secrets.

**Weiter:** Neue Runtime in eigenständiger langer SRT-N5-Kohorte qualifizieren;
Original-Recorderverlust und alte UNKNOWNs bleiben offen. Danach N3/N4 und
bestehende Default-DDS-N5-/Age-/Clock-/Security-/Ressourcengates. M3 weiterhin in
Arbeit, PR #2 Draft; Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: Lange N5-Kohorte und unabhängige Trace-Lanes

- Neue eingefrorene Kohorte ffd4fb2 / Command-Fix 899a6eb: drei geplante 300-s-
  SRT-N5-Fälle, Labels 1701/2903/4211, Command-/Recorder-Diagnostics und native
  V2-Aufnahme explizit an. 168 Quellen, acht ausgewählte installierte Dateien
  und installierte Scriptbytes bis Kohortenende konstant. Frische private Labs,
  keine Retries/Ersatzfälle/Tuningänderungen. N5 ohne stochastischen Loss/Delay;
  Labels keine unabhängigen Random-Loss-Samples.
- 1701 bestanden: 115 SUCCEEDED/Effekte, 35 Skipped, keine Expiry/Uncertainty/
  Nonadmission, keine PCAP-Drops. Traces 359/4/4 Records vollständig. Vier
  Clock-Deferrals, alle entsprechenden Intents erfolgreich. Max. gemessener
  Publikations-Age-Upper-Bucket 187 ms innerhalb 250-ms-Gate.
- 2903 **fehlgeschlagen** wegen Diagnostic Completeness: Operatortrace 397 von
  398 Attempts, Dropped=1, Sequenz 235 fehlt; keine Rekonstruktion. Dennoch
  Application-Fenster vollständig: 129 SUCCEEDED/Effekte, 21 Skipped, keine
  Expiry/Uncertainty/Nonadmission, null PCAP-Drops; ein Clock-Deferred-Intent
  erfolgreich. Robot-Traces vollständig, je vier Records. Max. Age-Bucket 227 ms.
- 4211 wegen Fail-fast nicht ausgeführt. 244 bestätigte Effekte, vier geschlossene
  Journale identisch inkl. Result-Rate/Generation, acht Cgroup-Fenster und beide
  Source-Summaries exakt reproduziert. Source/Published/Observer: 75032/26236/26236
  und 75033/27637/27637. PCAP Captured/Filter/File je Endpoint 108712 / 109964,
  Kerneldrops und native Reserve-/Copy-Verluste null. Realtime-PCAP-Fenster bleiben
  clockbedingt unterdrückt. Keine Performance-/Physical-Delivery-Inferenz.
- Archivierung erhält beide gemeldeten image_platform_id-Werte: einmal Manifest-
  Digest, einmal Config-artig. Immutable Config.Image-Referenz und aufgezeichnete
  Container.Image-Werte sind in beiden Fällen identisch, Boot ebenfalls. Keine
  Rohfelder überschrieben/kanonische Config-ID erfunden; Ressourcenkosten nicht
  unter Annahme identischer Roh-Platform-ID-Felder vergleichen. Inspect-/Env-Dumps
  bleiben lokal, im Archiv nur selektierte Isolation-/Image-/Clock-Projektionen.
- Alter Tracebuffer verlor bei Full ODER Mutex-Contention; kombinierter Zähler
  belegt keinen eindeutigen Mechanismus. dc4131c entfernt den Contention-Pfad:
  zwei feste SPSC-Lanes, jeweils 128 Records, total weiterhin 256. Je Owner genau
  ein Producer, ein externer Consumer, Producerwechsel nur nach Join; Acquire/
  Release-Indizes sichern Slots. Kein Producer-Mutex/Retry/Callback/I/O. Full-
  Drops weiterhin explizit und Diagnostic-Gate unverändert strikt. Andere
  Reservationsverteilung = neuer Observermodus, braucht eigene volle Kohorte.
- Validiert: fünf fokussierte SDK-/Native-Tests (Trace/Overflow/Reservation,
  IPv4/IPv6 Endpoint-Recovery und Clock-Deferral/Revocation), ergänzender Test
  0a1c1b0 mit 2000 garantiert interleaved Observations bei maximal einem offenen
  Event je Lane und null Loss; 36 ROS-reported Tests und 92 Hosttests bestanden.
  Voriger voller SDK-Lauf 68 Tests gehört zum Kohortenruntime; kein erneuter
  voller 68-Test-/M2-Acceptance-Lauf nach Trace-Patch behauptet. Consumer neu gebaut.
- Getrennter 15-s-N0-Smoke des neuen Tracebuffers: acht Erfolge/Effekte, Traces
  34/4/4 vollständig, null Trace-/PCAP-Drops. Keine N5-Qualifikation daraus.
  Wire/Worker-IPC/Journal-/Command-/Deadline-/Lease-/Replay-Policy unverändert.
- Evidenz: evidence/m3-srt-n5-fixed-2026-11-06/, Originalplan/-manifeste unverändert,
  Raw-/Source-/Binary-Hashes, read-only Journale, Capture-/Trace-Reanalysen,
  Cgroup-Projektionen, separater trace-buffer-fix/ mit Smoke/Tests/Freeze.

**Weiter:** Neue vollständige N5-Kohorte für den unabhängigen Tracebuffer einfrieren.
Bisherige Kohorte bleibt failed, dritter Fall unexecuted; nichts ersetzen/waiven.
N3/N4, Default-DDS-N5 und Age-/Clock-/Security-/Ressourcengates weiter offen.
Historische Recorderverluste und UNKNOWNs erhalten; M3 in Arbeit, PR #2 Draft,
Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: SPSC-N5 mit live beobachteter Unsicherheit

- Neue vorab eingefrorene Kohorte 649b4ce: Labels 1701/2903/4211 je 300 s,
  unabhängige SPSC-Lanes, beide Diagnostik-Observer und native V2-Aufnahme aktiv.
  168 Quellen, acht ausgewählte Dateien, installierte Scriptbytes, immutable
  Image-Referenz und gemeinsame VM-/Time-Namespace-Proof vorab fixiert.
- Erster Fall **failed am Command-Outcomes-Gate**, weitere zwei nicht ausgeführt.
  Originaler Harness bleibt development-passed (dort unresolved erlaubt),
  Originalkohorte failed; keine Umklassifikation/Retry/Ersatzfälle.
- 15 Versuche: 14 SUCCEEDED/Effekte, Intent 15 unresolved, 135 Skipped,
  keine Nonadmission. Senderjournal 15 UNKNOWN/reconcile-required, Revision 0,
  ungültiges Result; Receiver ohne Record. 14 gemeinsame Erfolge identisch inkl.
  Result-Rate/Generation, Device Generation/Effekte 14. Kein Nichtausführungs-
  beweis/Expiry/Erfolg/Replay aus NOT_FOUND oder Abwesenheit erfinden.
- Trace: SDK-Accept 15 bei ca. 34,039 s, Robot Sessionchange/Invalidation ca.
  37,517/37,519 s; Operator bei 42,470 s, Completion 42,478 s. Erstes beobachtetes
  UNKNOWN 43,305 s mit passender Entry-/Current-Owner-Epoche. Live-Kontextverlust
  innerhalb des Messfensters, nicht nur Teardown. Bestehende Events erklären
  den initiierenden Socket-/Session-Close noch nicht; keine eindeutige Ursache.
- Alle Traces vollständig: Operator 1496, Robot 4/7, Dropped überall 0. Beide
  PCAPs Captured/Filter/File exakt 150432, null Kernel-/Native Reserve-/Copy-Loss.
  Sechs Source-Bilanzen und vier Cgroup-Fenster reproduziert. Produced 74987,
  Published 11864, Observer 11863; Stage-Defizite nicht isolierter WAN-Loss.
  Max. gemessener Age-Upper-Bucket 238 ms innerhalb 250, Realtime-PCAP-Fenster
  weiter clockbedingt unqualifiziert. Keine Kosten-/Performance-/Physical-Inferenz.
- fd0107e ergänzt opt-in Cause-Events: session_action (30) mit SessionError und
  Close-Control/Close-Sensor/Flush-Bits 1/2/4; link_lost (31) mit Channel 0/1
  sowie Socketstate/Security-Timeout/Epoll-/Provider-/Decode-Ursache. Transport-
  Stopping trägt TransportFault. Nur schließende Actions, kein Sensor-Error-Flood.
  Alte Traces lesbar; Detailfeld erweitert Layout, Consumer neu gebaut. Kapazität
  weiterhin 256 Records, 128 je Owner; keine Producer-I/O/Callbacks/Policyentscheidung.
  Wire/IPC/Journal-/Deadline-/Lease-/Start-Fence-/Replay-Policy unverändert.
- Fünf fokussierte SDK-/Native-Tests bestanden, inkl. kontrolliertem Peer-Close
  auf IPv4/IPv6 mit Link-Cause und Session-Close vor Receiver-Teardown; 36 ROS-
  reported Tests und 93 Hosttests bestanden. Kein neuer voller 68-Test-/M2-Lauf
  behauptet. Separater 15-s-N0-Smoke: acht Effekte/Erfolge, Traces 42/5/5 integral,
  neue Cause-Felder ausgeübt, null Trace-/PCAP-Verlust. Keine N5-Qualifikation.
- Evidenz evidence/m3-srt-n5-spsc-2026-11-06/ mit unveränderten Plänen/Manifesten,
  Incident-Zeitpunkten, Read-only-Journalen, Source-/Binary-/Raw-Hashes, nativer
  Reanalyse und Cgroup-Projektionen; spätere cause-trace/ Tests/Freeze/Smoke
  getrennt. Rohcaptures/Prefixes/Journale/Clocks lokal, keine kompletten Inspect-/
  Env-Dumps oder Credentials publiziert.

**Weiter:** Live-N5-Reset mit Cause-Events gezielt reproduzieren und Initiator
qualifizieren, bevor erneut eine vollständige Kohorte versucht wird. Alte
UNKNOWNs/Recorderverluste erhalten. N3/N4, Default-DDS-N5 und Age-/Clock-/Security-/
Ressourcengates offen; M3 in Arbeit, PR #2 Draft; Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: Einmaliger Cause-Repro und Admission-Loss-Test

- Vorab festgelegter einzelner 300-s-N5-Diagnoselauf (Label 1701) bei 4a49595,
  getestete Cause-Event-Runtime fd0107e, native V2-Aufnahme und beide Observer an.
  Source-/acht ausgewählte Binärinventare vor/nach Lauf konstant. Keine Wiederholung,
  Ersatzfälle oder Tuning. Ergebnis **kein aktiver Reset beobachtet**; nicht als
  Erklärung früherer Fehler oder komplette N5-/M3-Kohorte auslegen.
- 133 Attempts/SUCCEEDED/Effekte, 17 Skipped, null unresolved/UNKNOWN/nonadmission;
  Traces 417/5/5 integral und null Trace-/PCAP-Verlust. Setup-/Teardown-Close-
  Events erhalten, aber vom aktiven Command-Fenster getrennt klassifiziert.
  133 gemeinsame Journalrecords stimmen in Immutable-/Statusfeldern inkl. Result-
  Rate/Generation überein, read-only/immutable mit Hashkontrolle.
- Produced/Published/Observer 75041/2327/2327, Defizite explizit und nicht isolierter
  WAN-Loss. Max. Publikations-Age-Upper-Buckets IMU 162 / Joint 159 ms innerhalb
  250-ms-Modellgate. Source-Summary und vier Cgroup-Fenster exakt reproduziert,
  sämtliche Realtime-PCAP-Fenster weiter clockbedingt unterdrückt. Keine Kosten-/
  Performance-/Physical-Delivery-Behauptung aus diesem Einzellauf.
- 32ccfc6 ergänzt ausschließlich einen nativen Admission-before-commit-Peer-Loss-
  Regressionstest: Transportempfang/Receiver-Journalbarriere abwarten, Receiver
  stoppen und neue Epoch/Session verbinden. UNKNOWN/reconcile-required Revision 0
  ohne gültiges Result bleibt trotz Peer-NOT_FOUND und nach ursprünglichem
  5000-ms-Budget erhalten; genau ein SDK-Handoff, kein Replay/Effekt. Kontrollierte
  Barriere liefert bekanntes Faultmodell, keinen Initiatorbeweis für den alten
  spontanen N5-Reset. Bestehender Worker-Hook, keine neue Produktionsschnittstelle.
- Beide Command-Endpoint-CTests IPv4/IPv6 bestanden, jeweils 195 Checks inkl.
  neuer Admission-Loss-Szene und bestehender Normal-/Result-Recovery-/Running-
  UNKNOWN-/Timeout-/Shutdown-Szenen. Kein neuer kompletter SDK-/ROS-/Host-Testlauf
  behauptet; Produktionscode/Binärinventare unverändert, nur Testquelle geändert.
  Admission-Phasen-Faultcoverage, keine komplette N4-/ROS-/Hardware-Abnahme.
- Evidenz evidence/m3-n5-close-cause-2026-11-06/ mit unveränderten Plänen/Manifesten,
  aktivem Cause-Fenster (leer), ursprünglichen Trace-Logs, ausgewählten Journal-
  Vergleichsfeldern, Cgroup-Replay und Raw-Hashes sowie separatem Native-Testlog.
  Rohcaptures/Prefixes/Journale/Clocks lokal; keine Inspect-/Env-Dumps/Secrets.

**Weiter:** Prospektiv begrenzten Diagnose-/Faultplan zur Unterscheidung Provider-
Verlust vs. lokale Session-/Clock-Entscheidung verwenden; Initiator bleibt offen.
Keine günstigen Läufe anstelle gescheiterter Kohorten einsetzen. Historische
UNKNOWNs/Recorderverluste erhalten; vollständiges N5/M3, N3/N4, Default-DDS-N5 und
Age-/Clock-/Security-/Ressourcengates offen. PR #2 Draft; Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: Flow-isolierte CONTROL-Stille und gerichteter Fault

- Keine weitere Zufallswiederholung: Native V2-Rohdaten des gescheiterten SPSC-N5-
  Falls read-only analysiert. Neuer Tooling-/Testcommit be70a6a:
  tools/m3_control_liveness.py prüft Capture-/Clock-Proof, Version/Interface/
  Counter/Hash und trennt UDP-4-Tuple plus SRT-Destination-Socket-ID. Keine
  Payload-Entschlüsselung; ID 0 nicht etablierte Connection-Identität, Routing-
  Identifier keine Authentizitätsgarantie. GSO/VLAN/über-MTU/kurze CONTROL-Header
  werden verworfen, Fenstergrenzen/Zensierung explizit.
- Alter operator→robot-Flow zuletzt an Robot bei 32,509061932 s beobachtet,
  Robot SessionChange 37,517303435 s: 5,008241503 s beobachtete Stille.
  Reverse-Flow zuletzt an Operator 37,468471351 s, SessionChange 42,469670811 s:
  5,001199460 s. Voll beobachteter operator→robot-Interarrival-Gap ca. 5,127 s
  an beiden Hooks. Neue Handshakes/Reconnect-IDs nicht dazugezählt. Native-Hashes
  identisch zum alten Archiv, keine Rekonstruktion/Umklassifikation.
- Passend zum Default-Peer-Idle 5000 ms im gepinnten Provider 52be7c86… . Relevante
  Source-Dateien stimmen bytegenau mit Pin überein. Kein historischer Per-Socket-
  Readback, keine eindeutig belegte interne Idle-Branch-/Initiatorursache.
- Qdisc-Root-Delta über ganzen Lauf: Robot 1755730, Operator 331. Child-Counter
  überlappen und werden nicht summiert; keine Flow-/Zeitfenster-Loss-Zuordnung.
  Tap im qualifizierten Fixture hinter geprüftem Egress-Qdisc: SDK-Scheduling,
  Socket-/Queue-Verhalten und Pre-Hook-Qdisc-Loss bleiben offen, nicht pauschal
  WAN- oder Providerfehler behaupten.
- Neuer nativer Loopback-UDP-Gate-Test: CONTROL-Handshake bidirektional, danach
  nur listener→caller-Reply-Datagrams droppen; SENSOR direkt, beide Runtimeowner
  bis Fault aktiv. Provider-Control-Loss vor Session-Close ohne lokale Protocol-/
  Clock-Close-Ursache, Reverse-Forwarding bleibt positiv, Trace-Drops null.
  IPv4/IPv6 nach jeweils beobachteten 5004 ms; 631/619 Replies gedroppt, 213/208
  Reverse-Datagrams forwarded. Timeouts/Produktionscode/Dependency unverändert,
  keine globalen Netzwerk-/Qdisc-Eingriffe. Bewiesener kontrollierter Mechanismus,
  keine Gleichsetzung mit dem historischen Initiator/Pre-Hook-Ort.
- Beide Transport-Owner-CTests bestanden inkl. bisheriger Lifecycle/Cadence/
  Reconnect-Szenen (beobachtet 462/459 Checks); 98 Host-Python-Tests bestanden.
  Kein neuer voller SDK-/ROS-/M2-Lauf behauptet. Nur Analyse-/Testquellen geändert.
- Evidenz evidence/m3-control-silence-2026-11-06/ mit beidseitigen Flow-Fenstern,
  selektierten Altflows, Quellen-/Rohhash-Prüfung, Native-/Python-Testlogs und
  Grenzen. Keine PCAP-Payloads/Secrets/Inspect-/Env-Dumps publiziert.

**Weiter:** Unter vorab begrenztem Diagnoseplan Provider-TX-/ACK-/Queue-Beobachtungen
mit Operator-Egress korrelieren; Scheduling vs. Socket/Qdisc unterscheiden, bevor
Verhalten geändert wird. Historischer Initiator und vollständige N5-/M3-Abnahme
bleiben offen; alte UNKNOWNs/Fehler erhalten, N3/N4/Default-DDS-N5/Age-/Clock-/
Security-/Resource-Gates unverändert. PR #2 Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-06: Begrenzte CONTROL-Providerdiagnostik

- Neue optionale `TransportConfig::provider_diagnostics`, ROS-Parameter und
  Runner-Flag `--provider-diagnostics`, Default aus. CONTROL alle nominell 100 ms
  und vor Close im Drop-Pfad; `srt_bstats(...,0)` ohne Counter-Clear, tatsächliches
  Peer-Idle-Readback, Read-Brackets, Owner/Generation/Socket, Verfügbarkeit/Fehler,
  kumulative DATA/ACK/NAK/Bytes plus Buffer/Flight/RTT-Gauges. Separater SPSC-Puffer
  128 Records, Lifetimebudget 75000; Verlust/Exhaustion explizit und Runnerfehler.
  ROS serialisiert außerhalb des Owners, Finalstatus nach Join. Public Config
  geändert, SDK und alle ROS-Consumer rebuilt. Kein Policy-/Timeout-/Pin-Change.
- Parser hält beide Read-Brackets pro Delta, trennt Socketidentitäten und
  unavailable Samples, prüft Accounting und meldet mögliche 32-bit-Sättigung.
  SDK-Locks/Bookkeeping beeinflussen Timing; kein Nonblocking-/Zero-Overhead-
  Versprechen. Counter erfassen nicht Keepalive/Handshake/ACKACK, beweisen weder
  UDP-Stille noch Delivery. RTT 0 kann fehlender Estimate sein.
- 105 Hosttests, voller SDK-CTest 69/69 und ROS 36 reported Tests bestanden.
  Native gerichtete CONTROL-Stille mit Diagnostik IPv4/IPv6: 5005/5003 ms,
  tatsächliches Idle-Readback 5000 ms, 788/781 Checks; Counterwachstum trotz
  bekannter Gate-Drops und flacher Caller-DATA-RX nach Settling nachgewiesen.
- Prospektiver Plan, genau ein N0-Smoke und ein N5-90-s/Seed-1701-Lauf; keine
  Random-Retry. Quellstand 0ace537 (SDK/ROS eedf5d3), Sources/Install-Matches und
  acht Runtimehashes vorher/nachher gleich. N0 8 Erfolge/Effekte, keine UNKNOWNs;
  Provider 271/23/226 vollständig. N5 39 Erfolge/Effekte, 6 Slots übersprungen,
  keine UNKNOWNs; Provider 974/24/959 und Commandtrace 135/5/5 vollständig,
  null Drops/Exhaustion. Kein aktiver CONTROL-Loss/Close reproduziert; daher nur
  Instrumentierungsvalidierung, keine historische Initiatorzuschreibung/Fix.
- N5 max beobachteter Startgap 113,283167 ms, Readspan 0,673250 ms, keine Bounds.
  PCAP 39550 Records/Filter je Endpoint, zero Kerneldrops; Native 39598/39603,
  zero Reserve-/Copyverluste bei separaten Populationen/Intervallen. Realtime-
  PCAP-Fenster weiter withheld. N5 Source/Published/Observer 22534/7173/7173;
  Sensordefizit erhalten, keine Performance-/Lossless-Behauptung.
- Evidenz evidence/m3-provider-diagnostics-2026-11-06/ mit Originalmanifesten,
  Diagnoselogs, Outcomes, Accounting, Testlogs, Prospektivplan und Rohhashes.
  Payloads/Prefixes/Journale/Clocks lokal, keine Secrets/Inspect-/Env-Dumps.

**Weiter:** Mit eingefrorener Diagnostik einen begrenzten Plan zur Trennung von
Provider-Scheduling/Socket-Send und Post-Qdisc-CONTROL verfolgen. Historischer
Initiator/UNKNOWNs, volle N5-/M3-Abnahme, N3/N4/Default-DDS-N5/Age-/Clock-/Security-/
Ressourcengates offen. Alte Fehlläufe unverändert; PR #2 Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-06: CONTROL-only Egress-Faultharness, Versuch fehlgeschlagen

- Neuer opt-in Runner `--control-egress-fault operator|robot`, nur N0 >=45 s mit
  Command-/Provider-/Native-Diagnostik. Dedizierter tc-egress-u32/gact-Drop auf
  owned eth0, IPv4 UDP, Peer-/32 und CONTROL-Port 10080; SENSOR aus Selektor
  ausgeschlossen. Nach einem Drittel der Dauer, sechs Hostsekunden bis Restore;
  VM-Brackets um tc, Filtercounter und leeres Restore-Readback. Keine Default-/
  Policy-/SDK-/ROS-/Provideränderung. Kein N4-Phasen-/Historischer-Ursachenbeweis.
- Read-only-Analyzer für gepinntes Handle/Wire-ID-Mapping, alte Socket-/Tuple-
  Identität, vollständiges Native-v2/Common-Clock-Fenster und nur benachbarte
  verfügbare Providerdeltas mit beiden Reads komplett im aktiven VM-Intervall.
  Reverse-CONTROL/SENSOR/Restore separat. Host-getestet, live nicht validiert.
- Prospektiv genau ein 45-s-N0/Seed-1701-Versuch, b0e2204, alle 178 Sourcehashes
  passend; acht Runtimehashes vorher/nachher identisch zum vorigen Testbuild.
  Lokal .local/m3/20261106T203905001506Z. Filter erfolgreich installiert, aber
  `tc ... filter show ... pref 49152` lässt `pref` im JSON aus. Validator nahm
  fälschlich Pflichtfeld an: `unexpected CONTROL filter`, Abbruch vor verifiziertem
  Sechssekundenintervall/Restore. Initialcounter 0, kein Lifetimecounterbeweis.
- Originalmanifest FAILED erhalten, inklusive sekundärer fehlender Endpoint-
  Measurements und finaler Command-/Providerstatus. Keine Rekonstruktion/Rescue.
  Beide Container und Netzwerk erfolgreich entfernt. Kein zweiter Liveversuch.
- Parser akzeptiert fehlendes pref nur im festen scoped Query; explizit falsches
  pref/Protocol/Kind/Action/Counter weiter Fehler. Originalreadback als Fixture.
  Install-Readbackfehler entfernt Filter vor Raise, Finalstatsfehler ebenfalls
  im finally mit Restorecheck. Fehlerpfade getestet. 112 Hosttests vor Versuch,
  115 nach Fix bestanden, Syntaxchecks bestanden. Keine frischen SDK-/ROS-/M2-
  Tests behauptet; Runtime unverändert (vorherige 69 SDK/36 ROS gelten dafür).
- Evidenz evidence/m3-control-egress-fault-2026-11-06/ mit Plan, Originalmanifest,
  tc-/Fehler-/Diagnose-/Cleanup-Logs, Findings, Source-/Runtimeprovenienz und
  Rohhashes. Payloads/Prefixes/Journale/WALs/Clocks lokal, keine Secrets/Inspect/
  Env-Dumps. Kein erfolgreich validiertes Provider-vs-Egress-Signature behauptet.

**Weiter:** Korrigierten Harness unter frischem prospektiv begrenztem Plan live
validieren; alten Fehlversuch erhalten. Danach qualifiziertes Signature für N5-
Triangulation nutzen. Historischer Initiator, volle N5-/M3-Abnahme und sonstige
Gates offen; PR #2 Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-06: Korrigierter CONTROL-Faultharness live validiert

- Frischer vorab commiteter Ein-Ausführungsplan cd54446, N0/45 s/Seed 1701,
  operator→robot CONTROL-only tc-Drop. Alter FAILED-Versuch unverändert. 115
  Hosttests/Syntaxchecks bestanden; Sourcehashes und acht Runtimehashes zum
  vorher getesteten SDK-/ROS-Build vorher/nachher gleich. Keine Runtime-/Policy-/
  Timeout-/Dependencyänderung, keine frischen SDK-/ROS-/M2-Tests behauptet.
- Lokal .local/m3/20261106T213402911275Z. Filter installiert/validiert/entfernt,
  leeres Restore-Readback. Finaler Pre-Remove-Counter 303 Drops/39356 Bytes,
  kein garantierter Lifetimecounter. Garantiert aktives VM-Intervall 6,410313587 s,
  angefordert sechs Hostsekunden. Keine Epoch-Subtraktion/Exaktdauerbehauptung.
- Bekannte Signature beobachtet: operator gleiche Socketidentität, 43 verfügbare
  benachbarte Readpaare komplett im Intervall: DATA-sent +137 inkl.135 Retransmits,
  ACK-sent +159; Post-Filter-CONTROL out 0, Robot alter CONTROL in 0. Reverse alter
  CONTROL am Operator 159, SENSOR-Source je Hook 1046 plus262 Parity, nach Remove
  im Drei-Sekundenfenster CONTROL out je92. Countertypen/Zeitgrenzen verschieden,
  keine Summierung von Retransmits auf DATA/keine exakte Dropgleichheit.
- Robot LinkLoss 5,001006502 s nach letztem alten incoming CONTROL, dann Close
  ohne SessionError. Operator-Loss ca.1,195 ms später. Anders als historische
  ca.fünf Sekunden Endpoint-Close-Abstand; kein Beweis desselben N5-Initiators.
  Bekannte Filterursache dieses Experiments, keine Rückwärtsattribution.
- Acht bestätigte Erfolge/Effekte, Intent9 UNKNOWN/reconcile-required Revision0
  ohne gültiges Result, 14 Slots übersprungen. Immutable geschlossene Journale:
  neun Sender-/acht Receiverrecords, acht Erfolge/Hashes/Kontexte/Resultate passen;
  Receiverdeadline konservativ früher, nicht Gleichheit unterstellt. Für9 genau
  ein SDK-Handoff, Receiverrecord fehlt, Peer-NOT_FOUND und UNKNOWN nach Budget
  erhalten. Keine Nonexecution/Expiry/Replay-/Result-Erfindung. Harness PASSED
  erlaubt UNKNOWN und bedeutet keine Qualification-Abnahme.
- Providerlogs643/22/604, Commandtrace371/5/10 vollständig, zero Drops/Exhaustion.
  Max Readspan2,519750 ms/Startgap114,167500 ms beobachtet, keine Bounds. PCAP
  23862 Records/Filter je Endpoint zero Kerneldrops, Native23879/23882 zero
  Reserve-/Copyverluste bei separaten Populationen. Realtimefenster withheld.
  Source/Published/Observer11291/10258/10248, alle Conservationbalances0.
- Evidenz evidence/m3-control-egress-validation-2026-11-06/ mit neuem Plan,
  Originalmanifest/Logs/Result, unabhängiger Provider-vs-Egress-/Flowanalyse,
  Journalvergleich, Inventaren/Testlog/Rohhashes. Payloads/Prefixes/Journale/
  Clocks lokal; keine Secrets/Inspect-/Env-Dumps. Historische Fehlläufe unverändert.

**Weiter:** Validierte Unterscheidung in separatem prospektiv begrenztem N5-
Diagnoseplan mit Providerdaten/Flowisolierung anwenden. Historischer Initiator,
UNKNOWNs, volle N5-/M3- und sonstige Gates offen. PR #2 Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-06 UTC: N5 Provider-vs-Egress mit ARP-Hinweis

- Neuer Read-only-Analyzer m3_control_provider_liveness.py, vorab Plan/Code
  e29412c, 120 Hosttests/Syntaxchecks und bekannte Filter-Signature gegengeprüft.
  Genau ein N5/300s/Seed1701 ohne Inject-Fault, Runtime/Pin/Policy/Timeouts gleich.
  Alle Sourcehashes und acht Runtimehashes passen. Keine neuen SDK/ROS/M2-Tests.
- Lokal .local/m3/20261106T230052361493Z: 126 bestätigte Erfolge/Effekte, 24 Slots
  übersprungen, keine UNKNOWNs/aktiven CONTROL-Loss-/Close-Events. Kein Reset
  reproduziert, keine alten Kohorten ersetzt. Journale126/126 immutable gelesen,
  Erfolgs-/Kontext-/Resultfelder passen, genau ein SDK-Handoff je Intent,
  Dispatch jeweils vor konservativer Receiverdeadline, Deadlines nicht gleichgesetzt.
- Alle vier vollständig beobachteten alten CONTROL-Egressgaps >=1s erhalten:
  Operator1,000311417s DATA/ACK/NAKdelta0; Operator4,237048752s DATA364 inkl350
  Retransmits, ACK68/NAK1; Robot1,099705168s DATA15 inkl14Retransmits; Robot
  1,054902209s DATA35 inkl28Retransmits/ACK15. Source-CONTROL out aller Flows
  jeweils0. Peer je eine Edge-Beobachtung19–24us nach Leading Edge, keine leeren
  Peerfenster oder sichere Paketauthentifizierung behauptet. Größter Gap39
  benachbarte verfügbare same-identity Readpaare komplett innerhalb des Gaps.
- Aktuelle Beobachtung grenzt Unterschied zwischen Provider-Sendaccounting und
  Tap ein, nicht eindeutig Socket/Neighbor/Qdisc. Flatcounter kein UDP-Abwesenheits-
  beweis; Retransmits in DATA enthalten, fehlende Kontrolldatagrammtypen beachten.
  Whole-run Rootdrops Operator184/Robot618355 ohne Flow-/Eventattribution,
  überlappende Childcounter nicht addieren.
- Explorativ NACH Messung neuer ARP-Extractor m3_arp_gap_observations.py mit
  Header-/Repräsentations-/Hashchecks; alle vier vorher ausgewählten Gaps,
  Duplikate retained. Vier neue Parsertests, insgesamt124 Hosttests bestanden.
  Größter Operatorgap: fünf outgoing ARP-Requests zum Robot; Robot outgoing Reply
  30,542us und Operator observed Reply19,792us vor CONTROL-Resume. Robotgap
  1,0549s ebenfallsReply76,375us vor Resume. Hinweis auf Neighborresolution in
  DIESEM Lauf, keine Neighborzustände/Kernelqueues/Dropstages beobachtet und
  keine historische Initiatorzuschreibung. Explorative Analyse keine Gateänderung.
- Provider2993/24/3054, Trace397/5/5 vollständig, zero Drops/Exhaustion. Max
  Readspan0,623041ms/Startgap113,664291ms beobachtet, keine Bounds. PCAP121477
  Records/Filter je Endpoint zero Kerneldrops, Native121569/121567 zero Reserve/
  Copyverluste bei anderen Populationen. Realtimefenster withheld. Competitor
  ~128023bits/s whole-run angeboten, 1235Alivechecks, kein Windowdeliverybeweis.
  Source/Published/Observer75024/23032/23030, Conservationbalances0; Defizit erhalten.
- Evidenz evidence/m3-n5-provider-liveness-2026-11-06/ mit Prospektivplan,
  Originalmanifest/Logs, primärer Flow-/Provideranalyse, Edge-/All-Flow-Crosscheck,
  explorativen ARP-/Interfacebeobachtungen, Journalaudit, Tests/Inventaren/Rohhashes.
  Payloads/Prefixes/Journale/Clocks lokal, keine Secrets/Inspect-/Env-Dumps.

**Weiter:** Begrenzte read-only Neighborzustandsbeobachtung und prospektiver
Fixture-Kontrast zur Neighborresolution in owned N5-Lab. Jede Neighbor-Konfig-
Änderung separater Diagnosekandidat, kein Ersatzbaseline. Historischer Initiator/
UNKNOWNs, volle N5/M3 und übrige Gates offen. PR #2 Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-07: Neighbor-State-Paar und historische ARP-Assoziation

- Opt-in --neighbor-diagnostics, read-only peer-scoped ip-neigh-show, nominell
  100ms, Read-Brackets/Sequenz/ABSENT/Fehler, Limit75000 und Finalstatus. Keine
  aktiven Probes, aber Subprocess/Netlink-Overhead. --neighbor-mode permanent
  separater L2-Diagnosekandidat nur owned N0/N5 mit echten Peer-MACs, State/MAC
  über alle Samples/Finalreadback geprüft. Dynamic bleibt Default, Host unverändert.
- Vorab Plan41e6f60, genau ein N0-15s-Preflight permanent:8Erfolge, vollständig.
  Danach vorab Code035100b, genau ein geordnetes Paar N5/300s/Seed1701 dynamic,
  dann permanent. Gleicher VM-Boot, Observermethoden/Image/Runtime/Shaping gleich;
  Reihenfolge/Scheduling weiter Confounds. Acht Runtimehashes vorher/nachher
  gleich; gemessene Sourcehashes gegen jeweilige gefrorene Commits geprüft.
- Dynamic lokal .local/m3/20261107T074709774864Z:130Erfolge/Effekte,20Skips,
  keine UNKNOWNs/aktiven CONTROL-Resets. Alle3alten Egressgaps>=1s mit wachsenden
  Sendcountern und INCOMPLETE-Samples am Sender:Operator3,232864418s (31Samples),
  Robot1,141203625s (10),Robot1,058229125s (10). Edge-Reads getrennt, keine
  exakten Transitions-/Kernelqueue-/Dropursachen abgeleitet.
- Permanent lokal .local/m3/20261107T075252504462Z:132Erfolge/Effekte,18Skips,
  keine UNKNOWNs/aktiven CONTROL-Resets. State/MAC über3167/3170Samples stabil.
  Trotzdem2Gaps:Operator1,000092084s flatselected (kein UDP-Abwesenheitsbeweis),
  Robot1,314880584s DATA+17 inkl16Retransmits trotz PERMANENT. Neighborresolution
  also kein Alleinerklärungs-/Fixbeweis; keine günstigeren Ersatzbaselines.
- Nachträglicher historischer ARP-Check des alten Fehlfalls181823876229Z:
  Rohhashes passen altem qualifiziertem Flowarchiv. Alter Operator-Sourcegap
  5,127369086s enthält6 outgoingARPrequests, Reply am Operator5,250us vor
  CONTROLresume bzw119,106083ms nach Robot-SessionChange. Stärkt Hypothese
  Neighborbeteiligung, aber alte Neighborstates/Providercounter fehlen, keine
  exakte Kernelpfad-/Ursachen-/Nonexecutionzuschreibung. Alter UNKNOWN unverändert.
- Journale aller bestätigten Erfolge passen, je1SDK-Handoff/Dispatch vor
  konservativer Receiverdeadline. Neighbor/Provider/Trace/Native vollständig,
  keine Drops/Exhaustion/Reserve-/Copyverluste; PCAP125814(dynamic)/108233(permanent)
  Records/Filter jeEndpoint mit zeroKerneldrops. Native125902/125900 bzw108254/
  108257 bei anderen Populationen. Source/Published/Observer75023/19805/19805
  bzw75036/27570/27565, alle Conservationbalances0, Defizite erhalten. Realtime-
  fenster withheld, kein Performance-/Lossless-/Securityparitätsbeweis.
- Neighborreads bis44,683084ms/Startgap111,184208ms im Paar beobachtet, keine
  Bounds. 134Hosttests vorPreflight,136vorPaar,138final; Syntaxchecks bestanden.
  NachMessung nur Errorpath gehärtet: existierende Sample/Status/Ready-Dateien
  ohne Mutation verweigern, Budgetexhaustion getestet; nicht live wiederholt,
  erfolgreicher Messpfad unverändert. Keine neuen SDK-/ROS-/M2-Tests behauptet.
- Evidenz evidence/m3-neighbor-contrast-2026-11-07/ mit Plan/Originalmanifesten/
  Nachbardaten/Analysen/Journalaudits, historischer ARP-Auswahl, Provenienzen/
  Tests/Inventaren/Rohhashes. Payloads/Prefixes/Journale/Clocks lokal, keine
  Secrets/Inspect-/Env-Dumps. Alte Fehlläufe nicht verändert, Intrinsic/M4 unberührt.

**Weiter:** Verbleibenden Permanent-Neighbor-Gap vom Neighboranteil trennen und
Pre-Tap-Queue-/Dropstage lokalisieren, bevor Defaultfixture geändert wird.
Historischer exakter Initiator/UNKNOWNs und volle N5/M3/übrige Gates offen.
PR #2 bleibt Draft; kein neuer Default-/Transport-/Timeout-/Dependencyfix.

## Fortsetzung 2026-11-07: TC/Root-Stage qualifiziert, N5-PCAP-Population fehlgeschlagen

- Opt-in --control-qdisc-diagnostics (N0/N5, kein Classifierfault): software
  UDP-CONTROL/Peer-u32-gact-PASS pref49150, bestehende Hooks verweigert, Root-
  Config unverändert geprüft. Verdict/Workloadintervention, nicht passive AF_PACKET.
  Polling200ms/Limit37500, Filter-/Rootreads separat bracketed, Errors/Finalstatus,
  monotone Counter/Rootidentität und Gauges, Remove/emptyreadback. Default aus.
- Ursprungsplan708af1b synthetischer Probe FAILED beim netem->TBF-Wechsel gleichen
  Handles; Originalartefakte unverändert, ursprünglicher ROS-/N5-Plan gestoppt.
  Nur Fixturehelper gefixt: eigenen Root bei Kindwechsel explizit löschen, Generator
  idle, Classifier behalten; Receiver bei Fehler kooperativ stoppen. Regression.
  Frische Revisionf2010a1 einmal qualifiziert: baseline16counter/16tap/16receiver;
  Sensornegative4sent/0counter/4tap/4receiver; Root100%Loss16counter/0tap/0receiver;
  N5shaped16/16/16; Restore1/1/1. Native/PCAPidentitäten vollständig/gleich,
  Features unverändert, Filterentfernung geprüft. Nur aufgezeichnete Vethfixture.
- ROS N0-Smoke15s (f2010a1)8Erfolge vollständig. Danach genau1 N5/300s/Seed1701
  ohne Fault (83e9dd5), permanentNeighbor-Diagnosekandidat:129Erfolge/Effekte,
  21Skips, keine UNKNOWNs/aktiven CONTROL-Loss/Close-Events, kein vollständiger
  alter Sourcegap>=1s. Kein Residual-/historischer Fix, keine günstige Ersatzkohorte.
  Sourcehashes gegen gefrorene Commits und8Runtimehashes vorher/nachher passen;
  SDK/ROS/Pin/Timeout/Policy/defaultDynamic unverändert, keine neuen SDK/ROS/M2tests.
- WICHTIG N5-PCAPgate FAILED: Operator110671File/Captured/Filter, Robot110671
  File/Captured vs110673receivedbyfilter, beidezeroKerneldrops. Fileintegrität
  gültig, Robotpopulationfalse. OriginaldevmanifestPASSED mit populationfalse
  bleibt unverändert, keine Capturequalification/Rescue/Rekonstruktion/Retry.
  Realtimefenster ebenfalls withheld. Ursache der2fehlenden Records offen.
- Native110690jeEndpoint zeroReserve/Copyfailures, vollständig unabhängig von
  PCAPgate. TC1595jeEndpoint, Provider2995/24/3057, Trace405/5/5 vollständig,
  zeroDrops/Exhaustion. MaxTCread63,643833ms inN5/68,819250ms inklSmoke,
  Startgap210,192542ms beobachtet, keine Bounds/Zerooverheadbehauptung.
- Post-hoc Aggregate-Check (nicht neuer Gapgate): Counterendpunkte ganz innerhalb
  Nativecoverage, breitere volleNativepopulation. Operator6991PASSexecutions/
  6991selectedout, Robot14771/5122. Differenz zwischen Classifier und Tap,
  konsistent mit späterem Removal/Withholding; keine exakte Paketlosszahl,
  Edge/In-flight/Requeue-Semantik vorbehalten. Rootrobot92564Wholeifdrops,
  backlog/qlen0 am letzten Sample, keine CONTROL-Zuordnung. Residualgapnichtlokalisiert.
- Journale129Erfolge/Kontexte/Resultate passen, je1SDK-Handoff/Dispatch vor
  konservativer Receiverdeadline. SensorSource/Published/Observer75034/27873/
  27873, Conservationbalances0; Defizit erhalten, keine Performance-/Losslessclaims.
  144Hosttests vorProbe,145nachFix,148vorN5,149nachexplorativemAggregate-Boundarytest;
  Syntaxchecks bestanden. Analyseextension nachMessung separatprovenanziert.
- Evidenz evidence/m3-qdisc-stage-2026-11-07/ mit Original-/Revisionplan,
  erstemFAILED-Probe, qualifiziertemProbe, Smoke/N5Originalmanifesten/Logs,
  Zähler-/Neighbor-/Flowanalysen/Journalaudits/Tests/Inventaren/Rohhashes.
  Payloads/Prefixes/Journale/Clocks lokal; keine Secrets/Inspect-/Env-Dumps.

**Weiter:** Zwei-Record-PCAP-Filter/File-Shutdown-Diskrepanz unter begrenztem
Drain-Test prüfen und qualifizierten Stageobserver in deterministischem Queue/
Lossintervall einsetzen, keine spontanenN5-Wiederholungen bis günstig.
Defaultfixture/historischerexakterInitiator/volleN5-M3/übrigeGates offen,
PR#2Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-07: Capture-Drain-Klasse und deterministischer Child-Loss

- Vorab Plan/Code 23ffa00, 155 Hosttests und Syntaxchecks. Zwei frische finite
  UDP-Probes: tcpdump pausiert, 16 bekannte Sends, Native/Receiver aktiv.
  Abort vor Resume: File/Captured 0, Filter 16, Kernel-Drops 0, Native/Receiver 16.
  Erwarteter negativer Population-Gate, keine Capture-Abnahme. Resume/Drain:
  alle Populationen 16, keine Drops. Bekannte Klasse reproduziert, historische
  Zwei-Record-Ursache und alleinige Wirkung des Zusatzguards nicht bewiesen.
- Opt-in --capture-drain-check nach bisherigem Loadstop/1,25-s-Quiet: frische
  SIGUSR1-Statistik, PID/Startidentität, zwei stabile captured==filter-Snapshots,
  keine Kernel-Drops, fünf Hostsekunden Controllerbudget. VM-Signalbrackets und
  Host-Read-Zeit getrennt. Keine zukünftige Stille garantiert; finaler File/
  Footer/Population-Gate bleibt Pflicht. Default aus. Upstreamquellen und
  Grenzen gegenüber Distro-Patches dokumentiert.
- Genau ein N5/60-s/Seed-1701-Lauf, permanent-neighbor/TC/drain-Kandidaten:
  .local/m3/20261107T090553068812Z. --root-loss-burst robot ändert nur den
  bestehenden Child auf 100% Loss und explizit zurück auf 0%. Root/Classifier
  bleiben erhalten. Finalread-Fehler versuchen Restore im finally (getestet).
  Placement nach einem Drittel des Quellfensters, keine N4-Commandphasenbarriere.
- Angefordert zwei Hostsekunden, garantiert aktiv 2,370079501 VM-Sekunden.
  Vorab definierte +500/-100-ms-Margen ergeben 1,770079501 s Settled-Fenster.
  Acht TC-Readpaare vollständig darin: 217 selected PASS, Root-Drops +15563
  (ganze Schnittstelle), Robot CONTROL out 0, Operator CONTROL out 167.
  Drei Sekunden nach Restore CONTROL out Robot/Operator 106/114. Bekannte
  Signatur beobachtet. Der vollständige 2,578343668-s-Sourcegap umfasst auch
  Ränder außerhalb der Konfiguration; diese nicht eindeutig zuordnen.
  Permanent-State/MAC geprüft, keine aktiven CONTROL-Loss/Close-Events.
- 22 Erfolge/Effekte, acht Skips, keine UNKNOWNs. Journale/Kontexte/Resultate
  passen, je ein SDK-Handoff, Dispatch vor konservativer Receiverdeadline.
  Source/Published/Observer 15033/1941/1941, Conservationbalances 0, Defizit
  erhalten. Keine Physical-Delivery-/Performance-/Lossless-Behauptung.
- Live-Drain: zwei stabile Snapshots 32118 je Endpoint; finale File/Captured/
  Filter ebenfalls 32118, keine Kernel-Drops. Native 32144 je Endpoint ohne
  Reserve-/Copyverlust; Populationen nicht gleichsetzen. Alte PCAP-Diskrepanz
  110673/110671 bleibt FAILED, Realtimefenster weiter withheld. TC 404/404,
  Provider 700/20/675, Trace 78/5/5 vollständig ohne Drops/Exhaustion.
  Maximaler TC-Readspan 60,275959 ms/Startgap 210,175292 ms: Beobachtungen, keine Bounds.
- Nach Messung Finalfooterparser gehärtet: Inline-SIGUSR1-Statistik kann fehlenden
  finalen Footer nicht ersetzen. Alle Originalfooter mit strengem Parser
  nachgeprüft, Ergebnisse gleich. 157 Tests nach Settled-Analyzer, 158 final
  nach Footerregression, Syntaxchecks bestanden. Gemessene Sourcehashes gegen
  23ffa00 und acht Runtimehashes vor/nach passen; spätere Analyse/Parseränderung
  separat provenanziert. Keine frischen SDK-/ROS-/M2-Tests behauptet.
- Evidenz evidence/m3-drain-controlled-loss-2026-11-07/: Plan, Quellnotizen,
  Originalprobes/Livemanifeste und Logs, Pause/Signal/Readback/Drain, Analysen,
  Journalaudits, Inventare, Testlogs und Rohhashes. Payloads/Prefixes/Journale/
  Clocks lokal; keine Secrets/Inspect-/Env-Dumps. Intrinsic/M4 unverändert.

**Weiter:** Validierte Messguards für deterministische N3-DATA/FEC-Selektion und
N4-Commandphasenbarrieren verwenden. Spontaner Residualgap und exakte historische
Capture-/Resetursachen bleiben offen; kein Ersatz alter Fehlkohorten und kein
Defaultfix. Volle M3-Abnahme offen, PR #2 bleibt Draft.

## Fortsetzung 2026-11-07: Expliziter N3-Source-Selector synthetisch geprüft

- Code/Plan vor Messung 6990da6, 163 Hosttests und Syntaxchecks bestanden.
  tools/m3_sensor_fault.py: ein/zwei Source-Identitäten derselben Viererreihe,
  explizite Initialsequence/Row/Positions/Message/Socket/IPv4-UDP-Peers. Keine
  Origininferenz aus erster DATA-Beobachtung. Fixed IHL, keine Fragmente;
  DATA-/Message-/Socket-Matches erhalten Parität mit gleicher Last-Source-Sequence.
  Bestehende Classifierhooks verweigern, partielle Installation räumt eigenen Hook auf.
- Genau zwei neue finite synthetische Fixtures .local/m3-sensor-selector/1 und /2:
  je 12 Header plus Restore-Send. Eine Sourceposition droppt zwei Transmissions,
  zwei Positionen drei, inklusive wiederholter Identität mit Retransmitbit.
  Parität, SRT-CONTROL, andere Row/Socket/Message/Ports bleiben erhalten.
  Receiver/Native/PCAP identisch 11 bzw10 bekannte IDs einschließlich Restore;
  File/Captured/Filter ebenfalls11 bzw10 je Endpoint, zero Kernel-/Nativeverluste,
  bounded Drain stable_equal, Features unverändert, Filterentfernung geprüft.
- Keine authentisierte FEC-Recovery-/ROS-/Performance-Abnahme; run_m3 N3 bleibt
  gesperrt. SDK/ROS/Dependency und bisherige Fehlfälle unverändert. Quellenhashes
  gegen 6990da6 geprüft; Originalpläne/Readbacks/Logs/Resultate/Rohhashes unter
  evidence/m3-sensor-selector-2026-11-07/. Payloadcaptures/Secrets bleiben lokal.

**Weiter:** Vertrauenswürdige Live-Sender-Origin/Row/Message/Socket-Identität vor
Arming gewinnen, danach geplante ein/zwei DATA-Verluste mit authentisierter Parität,
Receiverrepair/-reject und bestehenden Messguards prüfen. N4-Commandphasenbarrieren
weiter offen; M3 nicht abgenommen, PR #2 Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-07: Authentisierte SENSOR-FEC finite Providerfixture

- Neue isolierte tools/m3_sensor_peer/main.cpp gegen unverändertes installiertes
  Providerarchiv gelinkt; öffentliche API, keine Bridge-/ROS-/SDK-Sourceänderung.
  SENSOR/GCM/32Byte/EnforcedEncryption/SESSIONAUTH/secured keys/FEC4 arqnever
  readbackgeprüft. Vor DATA SRTO_ISN an beiden Seiten gleich; accepted Handle ist
  beim Pin protocol_socket_id (socket_registry.cpp), nicht allgemein portabel.
  Source-/Message-/Socket-Identitäten und Origin per API plus Captures geprüft.
- Vorab Code/Plan94f4ade,166 Hosttests: genau geordnete Baseline/1Loss/2Loss.
  Baseline16Deliveries. 1Loss:15Source+4Parity je Tap, alle16Payloads vollständig,
  genau1Providerrepair, keine Retransmits/Undecryptable. PCAP69/66jeEndpoint,
  File/Captured/Filter gleich; Native vollständig, bounded Drain/Features passen.
- Ursprüngliche2Loss bleibt FAILED:14Deliveries wie erwartet, aber geplanter
  pktRcvFilterLossTotal=2 war falsch, tatsächlich0. Source: RowFecDecoder::expire_row
  meldet irrecoverableRanges nur für arqonreq, SENSOR arqnever liefert keinen
  generischen Unrecoverablecounter. Originalmanifest/Gate nicht umgeschrieben;
  vor Drain/Analysepfad abgebrochen, daher keine Drainqualification dieses Falls.
- Separat vorab Revisionplan/Code150eaf6,167Hosttests; genau1 frische2Lossfixture
  .local/m3-sensor-live-r2/2:14Deliveries, IDs6/7 am endlichen Cutoff absent,
  zweiTCdrops je1, 14Source+4Parity jeTap, keineRepair/Retx/Undecryptable,
  FilterLossReport0 separat von MissingIDs. PCAP64File/Captured/FilterjeEndpoint,
  Native/PCAP-Identitäten exakt, zeroCaptureverluste, stableDrain, Features gleich,
  Filterremove geprüft. Kein unendlicher Nonarrival-/ROS-/Age-/Physicalclaim.
- Original .local/m3-sensor-live/{0,1,2} bleibt unverändert. Evidenz unter
  evidence/m3-sensor-live-2026-11-07/ mit Plänen/Originalfailed/Revision/Readbacks/
  JournallosenPayloadresultaten/Counterlogs/Capturelogs/Provenienz/Rohhashes.
  Provider-/Fixture-/Observer-Inventar vor/nach gleich. Keine frischen vollen
  SDK-/ROS-/M2-Tests behauptet; Payloadcaptures/Secrets/Inspect-/Envdumps lokal.

**Weiter:** Vertrauenswürdige Verbindungsidentität und Selector in ROS-N3-Fälle
mit Windowaccounting, Publish-/Alters-/Orderingguards übernehmen. run_m3 N3 bleibt
noch gesperrt. N4-Commandphasen, bisherige N5/Capturefehler und volle M3-Gates offen;
PR #2 Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-07: ROS-N3-Fixture, Baseline an Admission-BUSY gescheitert

- Neue tools/m3_ros_sensor.py und m3_ros_sensor_scenario.py verwenden die
  unveränderten installierten SDK-/Bridge-/ROS-Binaries. 19 finite IMU-Samples
  bei angeforderten 20 Hz, mit Payloadhash-, ID-, Reihenfolge-, Alters-, QoS-,
  Clock- und sechs Conservation-Gates. Closed-Identity-Phase vor Arming: genau
  ein SENSOR_BIND/message1, Handshake-Origin und beide Taps stimmen überein.
  Measurement-Capture startet separat; der Gap ist explizit, keine Continuousclaim.
- Originalplan/Code 2f13689, 170 Hosttests: Baseline scheitert vor Arming am
  fünfsekündigen Stable-Drain unter laufendem CONTROL-Traffic. Captured/Filter
  jeweils gleich, aber fortlaufend steigend. Originalfehler und Cleanup bleiben
  unverändert; keine Samples, keine Ein-/Zwei-Loss-Ausführung.
- Separater Revisionsplan/Code f048464, 170 Tests: finite PCAP explizit nur SENSOR
  DATA/Parity/Handshake, Native weiterhin alle Frames. Filter im Image geprüft;
  Footer/File/Filter/Zero-Loss/Stable-Drain bleiben Pflicht für diese Population.
  Cooperative Abort beendet Pre-Arm-Waits; Cleanup überschreibt failed Drain nicht.
- Revision .local/m3-ros-sensor-r2/0 ebenfalls FAILED, diesmal Payloadgate:
  19 ROS-Publishes/Ingress, ein submit BUSY, null obsolete, 18 admitted/SDK-sent/
  decoded/published/observed. Source-ID 7 fehlt. Für Samples kommt BUSY in
  Impl::submit nur vom Shared-Mutex-try_lock-Miss; Holder/Dauer nicht beobachtet.
  Kein Network-Loss-, SDK-Retry- oder Republish-Fix eingeführt.
- Post-hoc: alle sechs Bilanzen null, nur Admission=1; 18 Payloadhashes stimmen,
  Age-Upper-Maximum 9643682 ns (Histogramm ceil10 ms). Identity-Capture geprüft;
  tatsächliche 18 Source + vier Parity pro Measurement-Tap stimmen mit PCAP
  überein. Zero Captureverluste, finale File/Captured/Filter gleich, Stable-Drain.
  Das ersetzt nicht den geplanten 19-Source-Gate. Finaler Featurevergleich des
  Successpfads wurde nicht erreicht und wird nicht behauptet.
- Genau eine Baseline pro Plan, keine ROS-Lossfälle oder weiteren Retries.
  evidence/m3-ros-sensor-2026-11-07/ enthält beide Originalfehler, Pläne, Logs,
  Metriken, Analysen, Provenienz und Rohhashes. Sechs selektierte Runtimehashes
  vor/nach gleich; keine neuen vollständigen SDK-/ROS-/M2-Tests behauptet.
  Rawcaptures/Journale/Resource-/Clockdetails lokal, keine Credentials/Inspectdumps.

**Weiter:** Bounded Sample-Admission-/SDK-Handoff-Identitäten korrelieren, damit
N3 tatsächliche angenommene Sourcepakete trifft, ohne BUSY zu verbergen, Samples
neu zu publizieren oder bis zu einer günstigen Baseline zu wiederholen.
ROS-Recovery/late-repair Ordering, volle 200/50-Hz-Multiroute/Seeds und N4-Phasen
bleiben offen. Provider-FEC-Evidenz separat, PR #2 Draft, M3 nicht abgenommen,
Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-07: Bounded Sample-Admission-/SDK-Handoff-Trace validiert

- Opt-in `sample_diagnostics`, Default aus. Zwei SPSC-Lanes mit je 128 Slots,
  75000-Record-Budget, expliziten Drops/Exhaustion. Genau ein ROS-Executor-Producer
  und ein Transport-Owner; Consumer formatiert JSON. Record ohne Allocation/I/O/
  Mutex/Retry. Andere submit_sample-Caller schreiben die ROS-Lane nicht.
- Admission: Original-Ingress, Headerstamp, Callbacksequenz, Route, Owner/Session/
  Generations, Bodygröße und SubmitResult inklusive BUSY. SDK: zurückgelieferte
  Message-Nummer, Envelope-Sequenz, Original-Ingress, Socket/Generation und
  SRTO_ISN-Readback. Opt-in srt_sendmsg2 nutzt dieselben TTL/Ordering-Defaults wie
  der gepinnte srt_sendmsg-Wrapper. ISN wird nach dem Send gelesen, statische
  Verbindungsmetadaten. Keine Policy-/Wire-/Crypto-/Timeout-/Retryänderung.
- Join über Source-Headerstamp zu Admission, dann Original-Ingress/Route/Owner/
  Session/Generations zu SDK. Lane-Sequenz ist keine Kausalitätsordnung; SDK kann
  vor ROS-Resultrecord fortschreiten. Kandidaten nur im ersten Single-Packet-
  Messagezyklus und mit Native/PCAP gegenprüfen. Queued ohne beobachteten Handoff
  bleibt unmatched; BUSY wird nicht wiederholt oder als SDK-Akzeptanz gewertet.
- Vorab Commit/Plan125f86f, SDK70 + ROS36 reported + Host176 Tests bestanden.
  Native IPv4/IPv6 prüft echte ISN/Message/Binding-/Sample-Metadaten und Original-
  Ingress. Queue-/Budget-/Concurrent-FIFO-/Overflow-/Parser-/BUSY-Negativtests.
- Genau eine neue Observervalidation .local/m3-sample-handoff/0, keine Lossfälle:
  19 Source/Admission/SDK/Publish-Joins, kein BUSY beobachtet. Sender39 Records
  (19 Admission +20 SDK inkl. Binding), Receiver0, keine Drops/Exhaustion.
  Measurement je Endpoint19 Source+5Parity, PCAP24File/Captured/Filter; Native/
  PCAP exakt, Stable-Drain, keine Captureverluste, Features vor/nach gleich.
  Sechs Bilanzen null, Payloadhashes/Order passen, Age-Upper-Max8701792ns.
- Nicht als Ersatz der früheren fehlgeschlagenen N3-Baseline oder BUSY-Fix werten.
  BUSY-Zweig in kontrollierten Trace/Parserfixtures geprüft, nicht neu live
  reproduziert. Admission-/Command-/Clock-/Pacing-/Retryvertrag unverändert.
  Transport/ROS vor dieser Messung neu gebaut; sechs Runtimehashes während Lauf
  gleich, nicht gleich zu altem Kohortenruntime behauptet. SRT-Archiv unverändert.
- Evidenz evidence/m3-sample-handoff-2026-11-07/ mit Plan, Originalresultaten,
  Trace-/Capturelogs, Build-/Testlogs, Provenienz, Inventaren und Rohhashes.
  Rawcaptures/Journale/Resourcetraces lokal, keine Credentials/Inspect-/Envdumps.

**Weiter:** Separat geplante ROS-Ein-/Zwei-Source-Lossfälle nach tatsächlicher
SDK-Messageidentität korrelieren; fehlende/reparierte Samples zu angenommenen
Callbacks mappen und unabhängige BUSY-Verluste erhalten. Late-repair Ordering,
volle 200/50-Hz-Multiroute/Seeds, N4-Phasen und M3-Gates bleiben offen.
PR #2 Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-07: ROS-Ein-Loss-Recovery validiert, zweiter Pre-Arm-Capture fehlgeschlagen

- Vorab Code/Plan38afa06,179 Hosttests und Syntaxchecks. Nur Hostharness/Tests
  geändert; sechs Runtimehashes wie vorher und während Messung gleich. Bisherige
  SDK70/ROS36-Validierung gilt für unveränderte Artefakte; keine neue volle Suite.
- Traced Lossmode mappt tatsächliche SDK-Messageidentität zu ROS-Admission über
  Original-Ingress/Route/Owner/Session/Generations und Source-Headerstamp. BUSY
  bleibt separat, verschiebt Source-ID, verbraucht keine SRT-Message. Originaler
  strikter19-Source-Gate unverändert. Shift-/Ambiguity-/Accounting-Regressionen.
- Genau eine geordnete Ein-/Zwei-Loss-Fixturefolge, keine Retries. Ein-Loss
  .local/m3-ros-traced-loss/1 PASSED:19 typed IMU bei angeforderten20Hz,19 SDK /
  Publish / Observer, kein BUSY. Message8/Row1Position3 gehört Source-ID6,
  Envelope7. Genau ein Classifierdrop, Wire-Source an beiden Taps absent;
  Same-sequence-Parity bleibt erhalten und vollständiger typed Payload kommt an.
- Measurement je Endpoint18 Source+5Parity,23 File/Captured/Filter, zero Native/
  Kernelverluste, Stable-Drain, Features gleich. Sendertrace39/Receiver0 Records,
  zero Drops/Exhaustion, Payloadhashes/Order passen, sechs Bilanzen null,
  Age-Upper-Max9398555ns. Keine ROS-FEC-Supplycounter neu gemessen.
  Post-hoc VM-Timing: SDK/Parity/ROS-Observation innerhalb garantiert aktivem
  Filterintervall; Callback-Ingress bis Observer2587625ns. Kein Physicalclaim.
- Zweite Fixture .local/m3-ros-traced-loss/2 FAILED VOR Arming: Robot-PCAP
  Captured8/Filter10, Operator8/8, zero Kernel-Drops; neun frische Snapshots
  unverändert ungleich bis Timeout. Kein armed-Marker, kein Measurementcapture,
  keine Samples/kein Zwei-Paket-Fault. Finalfooter bleibt8/10, nicht abgenommen.
- Post-hoc feste IPv4-Prefixpopulation: Native-selektiert8 und PCAP8 je Endpoint
  stimmen byteprefix/length-genau. Native insgesamt155/154 vollständig. Das
  erklärt zusätzliche Filtercounts nicht, beweist keine Abwesenheit vor Native-
  Attachment und rettet keinen Gate. Keine Zuordnung historischer Zwei-Record-
  Ursache, kein nachträgliches Passed/Retry/Subtrahieren/Rekonstruieren.
- evidence/m3-ros-traced-loss-2026-11-07/ enthält Plan, beide Originalmanifeste,
  Logs/Readbacks, Typedhash-Metriken, Timing/Capturevergleich, Provenienz,
  Inventare und Rohhashes. Rawcaptures/Journale/Details lokal, keine Credentials/
  Inspect-/Envdumps. Alte Fehlfälle erhalten, Intrinsic/M4 unverändert.

**Weiter:** Recorder-Startup-/Filterstatistik-Populationsscope qualifizieren,
bevor eine separat geplante Zwei-Loss-ROS-Fixture ausgeführt wird. Late-repair
Ordering, volle200/50Hz-Multiroute/Seeds, N4-Phasen und M3-Gates bleiben offen.
Ein-Loss-Recovery ist endliche Entwicklungsevidenz; PR #2 bleibt Draft.

## Fortsetzung: Filter-Lifecycle-Klasse und ROS-Zwei-Loss mit Pre-Bind-Recorder

- Vorab Probeplan/Code1b1610b,184 Hosttests: genau drei finite neue Fixtures.
  Je zwei bekannte Negative nach UDP39782 und16 Positive nach39781; Receiver
  bindet beide Ports, Native/Receiver sehen alle18 IDs. Installiertes libpcap:
  broad Filter nimmt2 Negative ohne Dispatch an, Narrowing behält Stats2,
  danach16 Positive -> File/Callbacks16 vs Receives18, zero Drops. Erwartete
  NEGATIVE Captureklasse, keine Abnahme/Subtraktion/Zuordnung alter Ursache.
  Final-filter-first Control und Pre-Bind-Kandidat jeweils16/16, Negative ausgeschlossen.
- tools/m3_packet_capture.py: nur opt-in finite Linux64-Ethernet-Fixture. Finalen
  BPF auf dead libpcap handle kompilieren, an AF_PACKET/SOCK_RAW protocol0
  anhängen, initial kernel0 prüfen, erst dann eth0/ETH_P_ALL protocol3 binden.
  VM-Brackets, Kernel-SO_TIMESTAMPNS, bounded128MiB/75000 Records, Truncation/
  Budget/Drops explizit. Zwei stabile Records==Kernel-Snapshots binnen5s,
  Schlusscheck, Filegröße/-hash und unabhängige Native-Identitäten sind Pflicht.
  Buffer angefordert32MiB, tatsächlich8MiB beobachtet; keine Performanceparität.
- Wahrheitsgemäße eigene Backend-Counter, alte tcpdump-Footer und Defaults
  unverändert. Wrapper prüft alten8/10 weiter als failed. Keine neuen Statistiken
  oder Rohdaten in alten Captureartefakten ersetzt. Historische Ursache unbewiesen.
- Separat vorab ROS-Plan/Code6ba6562,186 Hosttests: genau eine neue Zwei-Loss-Fixture
  .local/m3-capture-startup/ros-two-loss/2 PASSED mit explizitem packet-socket.
  19 typed IMU bei angeforderten20Hz,19 admitted/SDK, kein BUSY. SDKmessages7/8
  gehören IDs5/6; je ein TCdrop. Nur diese beiden IDs am endlichen Cutoff absent,
  sonst17 Payloadhashes/Order korrekt. Kein Replay/Unrecoverablecounter-Claim.
- Measurement je Endpoint17 Source+5Parity und22File/Dispatch/Kernel; Identity8/8.
  Trace39/0 Records ohne Drops/Exhaustion. Sechs Bilanzen null, nur Transportgap2,
  Age-Upper-Max8993897ns, Clock/QoS/Session/Features passen. Alle Recorder initial0,
  BPF vor Bind, stabile gleiche Drains, zero Native/Kernelverluste. Native zuerst
  starten, erst nach PCAP-Prozessende schließen. Getrennte Phasen, kein Continuousclaim.
- SDK/Bridge/ROS-Binaries nicht geändert/neu gebaut; sechs Runtimehashes vor/nach
  und zu vorheriger SDK70/ROS36-Tracevalidierung gleich. Keine neue volle SDK-/ROS-
  oder M2-Suite behauptet. Andere Recorder-Workload, keine Ressourcenvergleichsbasis.
- evidence/m3-capture-startup-2026-11-07/ enthält beide Vorabpläne, drei Probe-
  Originale und ROS-Original, Counter/Lifecycle/Bytecode, Typedhash-Metriken,
  Trace-/Capturelogs, Coverage, Tests, getrennte Provenienz, Inventare/Rohhashes.
  Rawcaptures/Journale/Details lokal; Credentials entfernt, keine Inspect-/Envdumps.

**Weiter:** Absichtlich verspätete Reparaturen und Ordering-/Reject-Grenzen prüfen,
anschließend volle200/50Hz-Multiroute/Seeds für N3. N4-Commandphasen und übrige
M3-Gates offen. Neue finite Zwei-Loss-Fixture ersetzt alten tcpdump-Fehlfall nicht.
PR #2 Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-08: Receiverentscheidung und Late-Repair-Replay geprüft

- SampleTrace Schema2, Punkt4 receiver_decision: tatsächliche recvmsg2-Message,
  ursprünglicher Source-Epoch/Session/Route/Ingress/Envelope-Sequenz, lokaler
  Receiver-Owner/Socket/Generations und SessionError vor apply. Bestehende bounded
  SPSC-Lane/Budget/Lossgates, Default aus. Alte Schema1-Source-Traces lesbar.
  Keine Admission-/Clock-/TTL-/Retry-/Wire-/Provideränderung.
- Vor erster Messung SDK70, ROS36 und Host190 bestanden. Native IPv4/IPv6 prüfen
  echte Receiver-Metadaten. Sessionregression: neueres Sample akzeptieren, älteres
  same-session Sample als replay12 ablehnen, Session aktiv und nächstes Sample
  akzeptiert. Source-Epoch-/Schema-/Vollständigkeits-/Timing-Negativtests.
- Vorab01db3b8: genau eine20Hz-Fixture .local/m3-ros-late-repair/1 FAILED.
  19 admitted,18 decoded/published, kein Receiver-Event für Message5, alle anderen
  akzeptiert. Sechs Bilanzen null, nur SDK-to-receiver gap1 statt erwartetem Reject.
  Native successor6->Parity103247708ns. Gepinnter Provider repariert Lücken mit
  20ms Deadline ab späterer Source; Befund konsistent mit Expiry, kein interner
  Expirycounter/keine exakte Retirementursache gemessen. Originalfailed erhalten.
- Separat vorab87922c3, Host191: genau eine5ms-requested Revision
  .local/m3-ros-late-repair-r2/1 PASSED. Gleicher Receiver-Trace-Runtime, nur Python-
  Scheduling/Harness geändert. Keine Deadlineänderung oder weitere Retries.
  Native successor->Parity11619584ns; ursprünglicher Callback->Parity18880709ns.
- 19 Source/admitted/decoded, kein BUSY; Message5/SourceID3/Envelope4 wird exakt
  als replay12 abgelehnt, nachdem IDs4/5 typed beobachtet wurden. Sonstige18
  Payloadhashes/Order korrekt, spätere Publikationen laufen weiter. Nur
  receiver_rejected1, SDK-to-receiver gap0, alle sechs Bilanzen null.
- Trace39/19 vollständig ohne Drops/Exhaustion, Measurement je18 Source+5Parity,
  23File/Dispatch/Kernel; beide Capturephasen initial0/filter-before-bind/stableDrain/
  Hash/Native-Gates bestanden. Features/Clock/QoS/Session passen. Accepted-Publish-
  AgeUpperMax10428575ns. Ordering wird vor Age ausgewertet: keine konservative
  Altersentscheidung für den abgelehnten Repair behaupten; Ursprung/Budget gleich.
- 5ms requested ist keine200Hz-Abnahme:19 Calls,18 Intervalle in116171459ns,
  etwa154,94Hz; Median6040146ns, Max12303750ns. Nur endliche Row-/Ordering-Evidenz.
- evidence/m3-ros-late-repair-2026-11-08/ enthält beide Pläne/Originale,
  Post-hoc-Analyse des Fehlfalls, Cadence, Trace-/Capture-/Build-/Testlogs,
  Inventare/Rohhashes und getrennte Provenienz. Sechs Runtimehashes über beide
  Messungen gleich; SRT-Pin/Quellen unverändert. Rawcaptures/Journale/Details lokal,
  Credentials entfernt, keine Inspect-/Envdumps. Kein neuer voller M2-Run.

**Weiter:** Phasentreue volle200/50Hz-Multiroute-/Seed-N3-Qualifikation mit
Admission-/SDK-Zuordnung und tatsächlicher Sourcekadenz; danach übrige N4-
Admission/Dispatch/Result-Commit-Barrieren. Historische Capture/Reset/UNKNOWN-
Fälle und übrige M3-Gates bleiben offen, PR #2 Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-08: Phasentreue200/50Hz-Source und N0-Multiroute-Bilanzen

- Source2edfe3c: default-off source_diagnostics im bestehenden C++-Simulator.
  Bounded10000 logische Payload-/Timingrecords; Hashing/JSON erst nach serialized
  Pause-Fence, keine Rate-/Admission-/Mailbox-/Retry-/Provideränderung. C++/Python
  kanonische Feldhashes ohne CDR-Padding, explizite skipped slots und Due-Phasen.
- Ein isolierter10s-Run .local/m3-source-preflight/1 PASSED:10.001907129s,
  IMU2001/joints501, gemessen200.061846/50.090447Hz. Keine Skips/Traceverluste/
  Observerlücken, alle Typedhashes passen. Keine Bridge/Transportaussage.
- Separat geplant99c4d1d, ein Run .local/m3-ros-multiroute/1 PASSED:
 10.057059463s,2012/503 produziert,200.058477/50.014619Hz, Skips0.
  N0, permanente Nachbarn als explizite Fixture, getrennte ROS-Domänen/LOCALHOST,
  gemeinsamer Boot/Time-Namespace, keine Commands/Faults/PCAP/Native-Captures.
- Source2515 -> typed ingress2515 -> SDK2429 -> receiver2429 accepted ->
  Typedobserver2428 (IMU1930/joints498). Fehlende87: BUSY1, ingress_replaced1,
  outbound_replaced84, receive_replaced1; sonstige Losses0, sechs Bilanzen0,
  leere stabile Checkpoints. BUSY IMU379 bekommt keinen SDK-Index.85 queued
  Inputs ohne Handoff bleiben individuell unmatched; keine genaue Stage pro ID
  aus Aggregaten erfinden. Akzeptierte IMU18 ohne Typedbeobachtung separat behalten.
- Source-/Sender-/Receiver-Traces2515/4945/2429 vollständig, keine Drops/Exhaustion.
  Source route/stamp -> Admission -> SDKMessage -> tatsächliche Sessionentscheidung
  -> Typedhashes geprüft. Eine Bindingmessage, zusammenhängende SDK-Nummern/ISN;
  keine unabhängige Paketidentitätsprüfung in diesem N0-Preflight behaupten.
- Accepted-Publish-AgeUpperMax IMU17576587ns/joints27740143ns. Routehistogramme
  passen zur Publikation, Clock/QoS/Session/Owner/Generations/Isolation passen.
  Kein Physical-Age-/Lossless-/Overhead-/Transportvorteil-/N3-Abnahmeclaim.
- Host206 Tests, ROS41 reported ohne Fehler/Skips, Syntax/diff sauber. SDK70 bleibt
  frühere volle Validierung; keine SDKänderung/Neusuite oder volle M2-Abnahme.
  Fünf Runtimehashes über Multiroute gleich. Owned Container/Netz entfernt,
  Passphrase gelöscht. evidence/m3-source-preflight-2026-11-08/ enthält beide
  Vorabpläne/Originale, Hashtraces, Metriken, Tests/Build, Inventar/Rohhashes;
  keine Inspect-/Envdumps/Journale oder Rawresources veröffentlicht.

**Weiter:** Sustained mixed-route SDK-Identitäten unabhängig capturen und N3-
Row-Faults mit BUSY/Replacement-Zuordnung prüfen, danach geplante Seeds. Aktuelle
Source-Traces auf10000 Records begrenzt; längere Läufe brauchen vorab deklarierte
bounded Fenster/Budgets. N4, übrige M3-Gates und historische Unsicherheiten offen.
PR #2 Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-08: Captured200/50Hz und Mixed-Route-One-Loss

- Vorab517a940: optional --capture / --losses1 im Multiroute-Runner. Bestehender
  packet-socket Recorder, getrennte geschlossene Identity-/Measurementphasen,
  Native zuerst starten/zuletzt schließen. Neue Prüfung actualSDK -> exakte
  Native-/Full-PCAP-Source/Parity-Multimengen, Bindingoffset/Partialrow/Wrap.
  Neue Mixedrow-/Repair-/Classifier-Zeitordnungsgates. Python-only, keine
  Produktions-/SDK-/ROS-/Provider-/Admission-/Mailbox-/Retryänderung.
- PLAN evidence/m3-multiroute-capture-2026-11-08/: genau ein Baseline-Run;
  nur nach dessen PASS genau ein One-Loss-Run. Beide PASSED, keine Retries.
  .local/m3-multiroute-capture/{baseline,one-loss}. Je Source2011IMU/503joints,
  keine skipped slots. Gemessen200.003710/50.025791Hz bzw200.001139/50.025148Hz.
- Baseline: Typed2426 (1928/498), Source2514 -> DDSgap2 +BUSY2 +outbound_replaced84
  =88 missing. SDK2426/receiver2426. Measurement je2426Source+606Parity,
  File/Dispatch/Kernel3032 gleich. Source-/Sender-/Receivertrace2514/4939/2426.
- One-Loss: Typed2431 (1933/498), BUSY6 +outbound_replaced77 =83 missing;
  sonstige Losses0. SDK2431/receiver2431; Measurement je2430Source+608Parity,
  File/Dispatch/Kernel3038 gleich. Traces2514/4946/2431. Unterschiede lokaler
  Admission/Replacement-Populationen sind keine kausale Performancevergleichsbasis.
- Vor Source-Arming selektierte Message8/Row1Position3 genau einmal gedroppt,
  Parity ausgenommen. Tatsächliche Row5/6/7 IMU,8 joints. Message8 mappt auf
  Jointcounter2/Envelopeseq2: Sourcepacket an beiden Taps absent, Rowparity da,
  explizit Session-accepted und exakter Typedhash/Stamp einmal beobachtet, während
  Classifier noch installiert. Native parity47375327895ns -> EntscheidungEnd
  47377568728ns -> Typed47378953561ns -> HookremoveBegin60051112984ns.
- Sechs Bilanzen jeweils0, leere stabile Checkpoints, sämtliche Typedhashes/Order,
  Clock/QoS/Session/Owner/Generations/Isolation passen. Alle Traces vollständig,
  keine Drops/Exhaustion. Unmatched IDs bleiben separat; Aggregate liefern keine
  genaue individuelle Stage. Keine lossless/PhysicalAge/Crypto-FEC-Abnahme.
- Identity je8/8, alle Recorder initialkernel0/finalfilter-before-bind/stabile
  gleiche Drains/Hash/Größe; keine Kernel-/Nativeverluste/Truncation/Exhaustion,
  Features unverändert. Separate Phasen, kein Continuouscaptureclaim. PCAP-
  Realtime nicht als qualifizierte Zeitbasis nutzen. Native ist skb, nicht Wire.
  AgeUpperMax Baseline IMU14011182ns/joints27148919ns, OneLoss14179458/29336477ns.
- Host210/Syntax/diff bestanden; letzte volle SDK70/ROS41 unverändert, nicht
  neu ausgeführt. Sieben Runtimehashes über beide Fixtures gleich. Owned Netz/
  Container entfernt, Passphrase gelöscht. Evidence enthält Pläne/Originale,
  Hashtraces/Metriken, Capturestatus/Lifecycle/Fault/Clock/Qdisc, Tests, Inventar
  und Rohhashes; keine Rawcaptures/Prefixes/Journale/Resources/Inspect-/Envdumps.

**Weiter:** Sustained Mixedrow-Two-Loss mit tatsächlicher Source/SDK-Zuordnung,
anschließend vorab geplante Seed-Repetitionen/übrige N3-Gates. Sourcebudget10000
Records bei längeren Läufen vorab beachten. N4 und übrige M3-Gates/historische
Unsicherheiten offen. PR #2 bleibt Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-08: Fullrate-Two-Loss und beobachtetes Child-Shutdown

- Vorabcb2468b, Host215: originale Three-Seed-Two-Loss-Planung stoppt beim ersten
  Run .local/m3-multiroute-two-loss/1701 FAILED. Sendertrace4944 vollständig,
  Receiverprefix2427 Events OHNE final SAMPLE_TRACE_STATUS. Original2903/4211
  NOT EXECUTED, keine spätere Fixture ersetzt diese Cases/verändert das Verdict.
- Legacy Driver.cleanup ignoriert Exitcodes und Forced-Kill-Ausgang nach5s.
  Kein ursprünglicher Childstatus vorhanden; kein Beweis für Crash/Kill/Timeout
  oder konkrete Footerverlustursache. Ursache UNKNOWN lassen. Post-hoc nur:
  source2514,SDK2429,metrics receiver2427,typed2426; BUSY3/outbound_replaced82/
  SDKgap2/observerDDS1, sechs Bilanzen0. Capture je2427Source+607Parity3034 gleich.
  Diese Diagnostik ersetzt NICHT fehlende Trace-Vollständigkeit.
- Source5d9b9f3/Host218: scenario_processes.stop_children protokolliert eigenen
  Childstatus vor SIGINT, VM-Bracket, Exitcode, ForcedKill, Endzeit. Preexisting
  Exit auch0/nonzero/deadline/kill ->failed; andere eigene Children weiteraufräumen.
  Fünfsekündige SIGINT-Grenze gleich, Killwait bounded5, Hostwait25 für zwei
  Children. Python-only nach Messfenster, keine Produktions-/SDK-/ROS-C++/
  Provider-/Source-Schedule-/Admission-/Retryänderung, kein Runtime-Rebuild.
- Separat DIAGNOSTIC-PLAN einmal lifecycle-1701 PASSED. Danach separat vorab
  053c9bf REPETITIONS-PLAN, je einmal lifecycle-2903/4211 beide PASSED. Keine
  sonstigen Messungen/Retry/Selectoränderungen. Alle3 Children vorher live,
  kontrolliert SIGINT ->exit0, keine Kills, alle finalen Tracefooter vollständig.
  Passing erklärt/heilt den ursprünglichen unbekannten Fehler nicht.
- Alle3 je2011IMU/503joints produziert, keine skipped slots; actualHz
  200.011802/50.027815,200.012079/50.027885,200.016820/50.029070. N0-base/base+1
  seeds ohne random impairment: Independent-start-Repetitionen, keine Random-
  Loss-Abdeckung/kausale Performancevergleichsbasis aus verschiedenen Losszahlen.
- Vor Source-Arming Message7/8 Row1Position2/3 selektiert, beide initial0/final
  genau1drop. Tatsächliche Row5/6/7 IMU,8joint. Msg7 mappt je auf IMUcounter6/5/5,
  Msg8 auf Jointcounter2. Beide Sourcekeys an Native/FullPCAP-Taps absent, Parity
  da, genau receiver-gap{7,8} am drained cutoff, keine ausgewählten Typedoutputs,
  danach beide Routen frisch beobachtet. Keine permanente Absenz/interne Expiry/
  generischer Irrecoverablecounter-Behauptung. Alte One-Loss-Reparatur unabhängig.
- Lifecycle1701: SDK2428/recv2426/pub2426/observer2426. DDS2/BUSY5/outbound79/
  SDKgap2, sonst0;88 missing. Measurement je2426Source+607Parity=3033.
  2903: SDK2432/recv2430/pub2429/observer2428. DDS1/BUSY2/outbound79/SDKgap2/
  receive_replaced1/observerDDS1;86missing. Capture2430+608=3038.
  4211: SDK2433/recv2431/pub2431/observer2431. DDS1/BUSY1/ingress_replaced1/
  outbound78/SDKgap2;83missing. Capture2431+608=3039. Sechs Bilanzen je0.
- Source/Sender/Receivertrace2514/4941/2426,2514/4946/2430,2514/4947/2431,
  keine Drops/Exhaustion; Typedhashes/Stamp/Order, Clock/QoS/Session/Owner/
  Generations/Isolation/leere stabile Checkpoints passen. AgeUpperMaxIMU/joints
  21441943/32156726,14827528/28653399,15522998/30660836ns; keine PhysicalAge-Aussage.
- Identity jeweils8/8; Native zuerst/zuletzt, Sourcewindowdeckung, Recorderinitial0/
  finalfilter-before-bind/strictstableDrain/Hash/Size, keine Native-/Kernelverluste/
  Truncation/Exhaustion, Features unverändert. Separate Capturephasen/PCAP-Realtime
  keine qualifizierte Zeitbasis, Native ist skb. Sieben Runtimehashes aller4 Runs
  gleich; Owned Container/Netze/Passphrasen entfernt. SDK70/ROS41 frühere volle
  Validierung, nicht neu ausgeführt. Host218/Syntax/diff passen.
- evidence/m3-multiroute-two-loss-2026-11-08/ enthält drei getrennte Pläne,
  Originalfailed + Post-hoc separat, Diagnostic/Repetitionen, Executionmatrix,
  Status/Lifecycle/Tracehash/Metriken, Inventare/Rohhashes und Tests. Keine
  Rawcaptures/Prefixes/Journale/Resources/Inspect-/Envdumps veröffentlicht.
  baselines/m3-plan.json führt neuen partial full_rate_followup, kein N3-Accept.

**Weiter:** Baseline/One-Loss-Seed-Repetitionen unter beobachtetem Cleanup,
vorab längere bounded N3-Fenster/Budgets (Source10000), übrige N4-/M3-Gates.
Ursache originaler Footer fehlt weiterhin, historische Unsicherheiten offen.
PR #2 bleibt Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-08: Short-Baseline/One-Loss-Repetitionen und30s-Baseline

- Vorab81a39e0, Host223: ein sechs Cases umfassender Stop-on-first-failure-Cohort
  mit beobachtetem Child-Shutdown, Reihenfolge B1701/B2903/B4211/O1701/O2903/O4211,
  je nominal10s. Alle sechs PASSED; nur danach genau ein vorab geplanter30s-
  Baselinepilot PASSED. Keine Retries/Selectoränderungen/alten Verdictänderungen.
- tools/m3_multiroute_cohort.py bewahrt Originalresultate, stoppt bei Fehler/
  Exception und markiert Rest NOT EXECUTED. Neue explizite10/30s-Fenster:
  sourcefence[nominal,nominal+1]s, Sourceallowance2750/7750, Sender5501/15501.
  Hardlimits Source10000/Sample75000/PCAP75000+128MiB unverändert. Kein größerer
  Buffer/Truncation oder heimliches Windowstitching. Nur Sourcepause-/Hostbarrier-
  Waits folgen deklarierter Dauer; Produktionsdeadlines unverändert.
- Fensterprüfung fordert Baseline/OneLoss SDKgap0/receiver_rejected0; TwoLoss
  bleibt exakt{7,8}/gap2. Alle bisherigen Source/Cadence/Hash/Context/Capture/
  Lifecycle-/Age-/Conservationgates bleiben. Python-only, keine SDK/ROS-C++/
  Provider/Admission/Mailbox/TTL/Retry-/Sourcescheduleränderung oder Runtimebuild.
- ShortcaseActualHz IMU/joints: B1701 200.017542/50.029251,
  B2903 200.067455/50.016864, B4211 200.030360/50.032457,
  O1701 200.010030/50.027372, O2903 200.054263/50.013566,
  O4211 200.037539/50.034253. Keine Sourceskips, alle Typedhashes/Stamp/Order passen.
- Source totals2514/2515/2514/2514/2515/2514. SDK/Receiver2432/2423/2431/
  2435/2434/2424, Publikationen2432/2423/2430/2435/2434/2424,
  Typedobserver2432/2423/2430/2435/2434/2423. Missing82/92/84/79/81/91 separat:
  B1701 BUSY2/outbound80; B2903 DDS10/BUSY5/ingress1/outbound76;
  B4211 BUSY4/outbound79/receive1; O1701 BUSY1/ingress1/outbound77;
  O2903 BUSY3/outbound78; O4211 BUSY2/outbound88/observerDDS1. Sonst0,
  sechs Bilanzen je0; Aggregate keine exakte individuelle Lossstage.
- OneLoss jeSDK8 =Jointcounter2, Row5/6/7IMU/8Joint, initial0/final1drop.
  Ausgewählte Source an beiden Native/FullPCAP-Taps absent, Parity da, explizit
  Sessionaccepted/exakter Typedhash noch vor Classifierremove; SDKbegin nach
  Install, Parity <=decisionEnd <=typed <remove. Keine Publishindexannahme.
- Capture source/parity jeB:2432+608=3040,2423+606=3029,2431+608=3039;
  jeO:2434+609=3043,2433+608=3041,2423+606=3029. AlleSDKkeys/Bindingoffset/
  Partialrows passen. Identity je8/8 separatgeschlossen, Native zuerst/zuletzt,
  volleSourcewindowdeckung; Recorderinitialkernel0/finalfilter-before-bind/
  stableequalDrain/hash/size, keine Native/Kernelverluste/Truncation/Exhaustion,
  Features gleich. Keine Continuouscapture-/PCAP-Realtime-/PhysicalWire-Aussage.
-30s-Pilot:30.053896430s, Source6011IMU/1503joints=7514,
  measured200.007344/50.010154Hz, Skips0. Sender14754Records<15501,
  Source7514<7750; Status/Traces vollständig. SDK/receiver7242, published/
  typed7241, missing273 =DDS3/BUSY9/ingress2/outbound258/receive1, sonst0,
  sechs Bilanzen0. Capture je7242Source+1810Parity=9052 File/Dispatch/Kernel.
  AgeUpperMax IMU23610879ns/joints28470853ns, Shortmax40929297ns (B2903 IMU).
- Alle7 Clock/QoS/Session/Owner/Generations/Isolation/stableempty/Payload-/Age-
  gates passend; je3Children vorherlive ->SIGINTexit0 ohne Deadline/Kill,
  alle finalen Tracefooter vollständig. SiebenRuntimehashes über7Runs gleich.
  SDK70/ROS41 frühere volle Validierung, nicht neu ausgeführt, keine volle M2-
  Abnahme. Host223/Syntax/diff passen. Owned Container/Netze/Passphrasen entfernt.
- Evidence evidence/m3-multiroute-matrix-2026-11-08/: Vorabplan, Cohort/Originale,
  Matrix, Tracemetadata/Typedhashmetriken, Capture/Fault/Clock/Qdisc/Lifecycle/
  Childstatus, Tests, Inventar/Rohhashes. Keine Rawcaptures/Prefixes/Journale/
  Detailresources/Inspect-/Envdumps veröffentlicht. baselines/m3-plan.json aktualisiert.

**Weiter:**30s-One/Two-Loss und vorab deklarierte längere Fenster/Budgets,
übrige N4- und M3-Vergleichs-/Age-/Security-/Resourcegates. Kurze B/O/TwoLoss-
Repetitionen jetzt für alle3 Basewerte aus getrennten Vorabplänen vorhanden;
N0 ohne random impairment ist keine Random-Loss-Coverage/kausaler Vergleich.
30s-Pilot nur Baseline, keine30sFault-/FullN3-Abnahme. Originaler fehlender
Receiverfooter bleibt FAILED/UrsacheUNKNOWN, originale skippedCases bleiben
unexecuted. PR #2 bleibt Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-08: Failure Detection und native N4-Commandphasen

- Userpriorität geändert: zuerst Failure Detection/N4, danach SRT-N5/DDS-Discovery,
  erst dann übrige N3-Dauer/Faults und matched comparison. Kein weiterer N3-Run.
- Vorab326c2c0: genau eine echte Failure-Control-Suite PASSED9 Klassifikationen,
  echte installierte Bridge/Recorder statt nur Processmocks. Cleanbridge SIGINT0
  mit Footer akzeptiert; Abort-6/Kill-9/Stall(deadline0.3s, forcedKill-9) verworfen;
  preexited0 auch mit gültigemFooter als unerwarteter Exit verworfen. Cleanlog
  bleibt erhalten, separate Kopie ohne Footer wird abgelehnt. Witness überall0.
  Recorder6 synthetischeUDP-Sends clean0/strict6Records; Kill-9 und RLIMIT_FSIZE64
  nachReady/Exit120 rejected, Parent protokolliert trotz fehlendemChildstatus.
  Core Dumps aus; keine Hostressourcen geändert. Abrupt-child Descendants werden
  spätestens durch Owned-PID-Namespace-Teardown entfernt. Kein historischerCauseclaim.
- N4first40bf968/admission-both FAILED vorOutage: Childguard fand Worker nicht;
  rest8 NOT EXECUTED. Separat30441d3 guardfix: eigeneThreadchildliste+exakteWorker/
  IPC-Args+T-State+PID/startticks, bounded1s readiness; Metadata zeigt /proc/exe
  /run/rosetta/rosetta stattWorkerbinary. Originalrejectmetadata fehlte, keine
  eindeutige retrospektive Ursache erfinden. Guard vorSIGCONT nochmals prüfen.
- Identity-cohort ersterCase FAILED nachOutage: falscheFixtureAssertion gleiches
  Deadline-NS inbeidenJournals. Tatsächlich Receiver537595890394 <Sender537601704201,
  um5813807ns konservativer. Rest8 NOT EXECUTED. ProduktionsClockMapper korrekt,
  Testannahme geändert: Sender exactIngress+5s; Receiver mappedExpiry>originalOrigin
  und<=Senderexpiry auf provenCommonVMClock. Owners/SourceSession/Ingress/Hash
  bleibengebunden, freshresume/dispatch nutzenReceiverlimit, keinBudgetextend.
- Separat d6c2cbb CLOCK-REVISION genau9 nativeCases PASSED:
  admission_before_commit, after_atomic_handler_start_before_effect,
  result_committed; je both/to-robot/to-operator. Dann90d3ae4 separat3 weitere
  dispatch_committed_BEFORE_execution_grant/start Cases allePASSED. Insgesamt12.
  ReadonlyWALBarrier: absent /DISPATCHING-effects0 /SUCCEEDED-validResult.
  Strictere OfflinePhaseOrderPrüfung der alten9 zusätzlich archiviert, kein neuerRun.
- Echte installierte CommandEndpoint/Transport/JournalWorker, expliziter simulierter
  Ratehandler. Rootnetem100% nurOwnedContainer, seed/loss/dropsReadback; VMhold2s,
  guaranteedgemeinsamerCut wegenSetupoverhead2.483631168..2.597214710s, keine
  Exact2.000s-Aussage. RestoreN0 vorWorkerResume. Ursprüngliche5sCommandbudget
  unverändert;20sCoordinatorwatchdog nurTestallowance fürabsichtlichgehaltenen
  Worker (keine Änderung anProduktionsdefaults). SDK/ROS-C++/Provider/API unverändert.
- Alle12 SUCCEEDEDmitmatching durableproof100Hz/gen1, je1Effect/1executeSDKHandoff,
  keineakzeptierteCommandwiederholung. SourceID/route/hash/epoch/originalsession/
  ingress/deadline/finalstate/reason/revision/result audit; Senderdeadlineexact5s,
  Receiver~5..6ms früher. QUERYs beobachtet; einzelneFinalProof kannSTATUS oder
  QUERYresponse sein, kein isolierterQuerykausalitätsclaim. Zwei weitereSettlesekunden
  ohnezweitenEffect/Handoff; restoredReady/Clock, leereOwnerfaults, boundedjoin/
  alleTransporte/Workerstopped. Tracesattempted==recorded,dropped0. Native9StopMax
  24.845042ms<5s, weitere3auch<5s. PositiveKürzeralsBudget-Cuts dürfenerfolgreichsein;
  safeReject/Expiry/0Effects und deadline/proofnegative Gaten sindhostgetestet.
- Host231/Syntax/diff und StandaloneC++Release/WerrorBuilds bestanden. KeineSDK/
  ROS/ProviderProduktionsänderung oderRebuild: SDK70/ROS41 früherevolleValidation,
  nichtneu ausgeführt, keinevolleM2Abnahme. FixtureELFzwischenfehlerhaftenRevs/
  Dispatchphase neugebaut, getrennteSource/Runtimeprovenienz; installierte4
  ProduktionArtifacts überalle12gleich. AlleOwnedNetze/Container/Secretsentfernt.
- evidence/m3-failure-n4-2026-11-08/ enthält5vorabPlan/Gatefreeze/Revisionsdateien,
  FailureControls/2FAILED-Cohorts samtunexecutedRest und12PASS, Journal-/Barrier-
  Proofmetadata, Netzwerk/VMBrackets/kernelcounts, nativeEvents/Trace/Stopped,
  Builds/Tests/Inventare/Rohhashes. KeineRawJournals/PCAPs/Core/Inspect-/Envdumps/
  Credentials veröffentlicht. baselines/m3-plan.json N4phase_followuppartial.

**Weiter:** N4 ROS-Sensorfrische, expliziterDeadlineOverrun, withheldResult/Query-
Recovery isolieren, Crash/Restart/UNKNOWN ohneacceptedCommandReplay. DannN5-
CONTROLProgress undDDSColdDiscovery entsprechendUserreihenfolge; N3später.
Native12Cases sindkeinevolleN4/M3-/DDS-/Hardware-/PhysicalAge-Abnahme. Historische
FooterursachebleibtUNKNOWN/alteFailedundSkippedCasesbleiben. PR2Draft, M4unberührt.


## Ergänzung 2026-11-08: verbleibende bounded N4-Gates

Die zuvor als nächste Schritte genannten ROS-Frische-, Deadline-Overrun-, isolierten
QUERY- und Crash/Restart-Entwicklungstests sind jetzt ausgeführt: 4 native +3 ROS-
Frische +3 korrigierte ROS-Restart-Cases PASS. Nachweise und Scope stehen in
[evidence/m3-n4-remaining-2026-11-08/README.md](evidence/m3-n4-remaining-2026-11-08/README.md).

- Native6s-Unterbrechungen überschreiten das ursprüngliche5s-Budget: Admission/
  Dispatch werden sicher abgelehnt, gestartete Arbeit verfällt; jeweils0Effects.
  Separat unterdrückte direkte Finalantwort wird per QUERY mit1Effect rekonstruiert.
- ROS200/50Hz über15s, beide/einseitige Cuts: vollständige Tracepopulationen,
  sechs Bilanzen0, frische Samples beider Routen nachRestore, beobachtete gemeinsame
  VM-Ingress→Callback-Maxima25.352125/23.417917/23.454333ms <=250ms. Verluste sind
  explizit bilanziert, keine PhysicalAge-/CrossHost-/Lossless-Aussage.
- Realer ROS-Restart mit persistentem externem Simulator: vorAdmission UNKNOWN
  trotzNOT_FOUND/abgelaufenerDeadline und0Effects; nachEffect/vorCommit UNKNOWN
  mit1Effect; nachCommit dauerhaftSUCCEEDED mit1Effect. Je1SDK-Handoff, originale
  Deadline, neuerReceiverOwner/Session, keinacceptedCommandReplay. Alle kontrolliert
  gestoppten Inkarnationen haben vollständige Footer; absichtlich gekillte nicht.
- Zwei frühere Restart-Fixture-Cohorts bleiben FAILED, Folgetests dort unexecuted.
  Explizites Schließen der SQLite-Observer und Eigentümer-konforme Inspektion
  korrigiert: keine Live-Reads gegen exklusiven Worker; nachStop oder stabile private
  DB/WAL-Kopie beim angehaltenen eigenen Writer. Erstursache nicht eindeutig belegt.
- Host239 PASS, StandaloneFixture Release/Werror und Syntax/diff PASS. Produktions-
  SDK/ROS/Worker/Provider unverändert; SDK70/ROS41 bleiben frühere volle Validation.
  Originale Rohartefakte/Fehler erhalten, Credentials und OwnedNamespaces entfernt.

**Nächster Schritt:** SRT N5-CONTROL-Progress und DDS-ColdDiscovery. In dieser
Änderung kein N5-Run. Breite N4/DDS-/kombinierteLast-/Hardware-/M3-Abnahme bleibt
separat offen; PR2 bleibt Draft, Intrinsic/M4 unberührt.


## Ergänzung 2026-11-08: N5-Progress und DDS-Coldstart

Vorab gefrorener Plan/Implementierung57f415b, genau5 frische sequenzielle Slots,
keine Wiederholung, alle ausgeführt. Siehe
[evidence/m3-n5-progress-2026-11-08/README.md](evidence/m3-n5-progress-2026-11-08/README.md).

- SRT N0/15s8Successes/Effects,0unresolved/0skipped; N5/60s23Successes/Effects,
  0unresolved/7skipped. Default dynamische Nachbarn,512kbit/s,16Packet-ChildQueue,
  128000bit/sCompetitor. Original5sStartbudgets und genau1SDK-Handoff jeIntent,
  passende geschlossene Journals, komplette Traces allerBridge-Inkarnationen.
  Keine Session-/LinkLost-Events im aktivenFenster beobachtet. Kein historischer
  Resetfix oder vollständigeN5Abnahme. Sensor15024produziert/5543beobachtet,
  alle6Bilanzen0, Defizite explizit. MaxTerminalObservation3421.882377ms,
  MaxAbstandzwischenIntents4023.803085ms, kein ZweiSekunden-Erfolgsgarantieclaim.
- DDS system/simultaneous FAILED vorMessfenster: Sender keine vollständigen
  EndpointMatches beobachtet; Receiver Matches, aber0empfangeneHELLOs. Lokales
  Journal/Handler/QoS bereit, keineCoordinatorFailure. Je46TimelineSnapshots.
  Ursache inDDS-/Kernelpfad nicht eindeutig lokalisiert; keineProtokoll-Reparatur.
- DDS system/control-first boundedPASS:2Successes/Effects,6skipped,0unresolved.
  Sender2LeaseExpirations, beidePeers imSourceFenster einmalnotReadygesampelt;
  eineFinalbeobachtung erst16087.948466ms nachAufruf im erlaubtenResultDrain.
  Original5s betrifftStart, nichtFinalresultzeit. Startreihenfolge allein löst
  kontinuierlichenProgress nicht.3772Source/1718CallbackSamples.
- Separater bestehender paced-sensors/simultaneous Kandidat8/8Successes/Effects,
  0skipped/unresolved/LeaseExpirations.3785Source/967Callbacks, deutliche
  Sensorreduktion bleibt Teil desResultats. Defaultsystem bleibt unverändert.
- Neue begrenzteDDS-Timeline2048Records:1Hz innerhalb gleicherPhase/Readiness,
  plusTransitionen, harteExhaustion-/Footer-/Populationgates. Nur lokaleSamples,
  keinRTPS-Decoder oderWireCauseproof. Peer/ParentAbort führt zu kontrolliertem
  Cleanup vorNamespaceTeardown; alleDDSChildreports clean0, auchFailedStartup.
  Der Elternprozess beendet denFailedStartup trotzdem alsFAILED.
- Alle5PCAPpopulationen file/filter/captured konsistent; keineRT-PCAPZeitautorität.
  Alle8Produktionshashes vorher/nachher/unabhängig gleich; Quellenmatch57f415b.
  Host245PASS/Syntax/diff; keinSDK/ROS-C++/Provider-Rebuild, SDK70/ROS41 frühere
  volleValidation. AlleOwnedContainer/Netze/Passphrasesentfernt. AlteFehler/UNKNOWNs
  bleibenunverändert; neueKontrolldaten ersetzenkeinenhistorischenRun.

**Weiter:** AsymmetrischeDefaultDDS-Discovery packetbezogen mit qualifizierter
Capture und vorabdefinierterGegenprobe lokalisieren; längereSRT-N5Progress-Cohort
vorabfestlegen. PacedKandidat separatführen, keineWiederholungbisgünstigesResultat.
N3/Clock/Security/Resources weiterhinnachgeordnet. PR2Draft, M3offen, M4unberührt.


## Ergänzung 2026-11-08: paketbezogene DDS-Discovery-Lokalisierung

Nur retrospektive Analyse aller6Original-PCAPs der3DDS-Slots aus57f415b; keine
neuenLiveRuns/Defaultänderungen oder geändertenWorkloadVerdikte. Siehe
[evidence/m3-rtps-discovery-2026-11-08/README.md](evidence/m3-rtps-discovery-2026-11-08/README.md).

- Isolierter tshark4.2.2 mitIPv4Reassembly, geprüfteOriginalhashes undFile/Filter/
  Footerpopulationen; Source/Peer-Tap undCallback strikt unterscheiden.
- DefaultFAILED hat6statt8CommandEndpointBindings: kompletteRobot-HELLO-Publication
  undOperator-HELLO-Subscription fehlen inbeidenCaptures. Alle beobachteten
  komplettenAdvertisements sindanbeidenTaps vorhanden; keinDatagramLossclaim.
- Trotzdem154identischeRobotHELLOs anbeidenTaps: ursprünglicher generierterROS-
  Deserializer, protokoll2/HELLO1/OriginalProcessUUID, semantischeReserialisierung
  mitausgeneriertemSchema abgeleiteterCDRPaddingmaske.6positive/negativeChecks
  vorherPASS. OpakeungebundeneDATA zunächstnull statt0zählen; Typnachweis separat.
  Originaldiagnostik HELLOreceived0 bleibtunverändert. Das grenztDiscovery/
  ReaderAcceptance ein, beweist aberkeineeinzigartigeKernel-/Middlewareursache.
- Control-first undpacedje8Bindings; letztere235Robot-/209OperatorHELLOs als
  Typkontrollenvalidiert. FragmentframesOp/Robot default106/109, control-first
  158/212, paced0/0; ohneDecoderReassemblyReference4/7,3/57,0/0. Teilheaderaller11
  defaultErstfragmente separat analysiert, nieGUID-Binding/komplettesAdvert daraus.
  FehlendeRobotHELLOAdverts keinerkonkretenverlorenenFragmentgruppezugeordnet.
- Analysekorrekturen/Fehlschläge separatarchiviert: INFO_DST-Feld, HEARTBEAT-Range,
  synthetischesDigestfixture, ungebundeneCounts, MF=True, Containerworkdir und
  unbestimmtesCDRPadding. Endanalysen438ae9d/Teilheader34d06a4 mitSHA-Provenienz.
  OriginalePCAPs/Journals/WorkloadVerdikte unverändert; vollePDML bleibenlokal.
- Host255PASS,6generierteCDRChecks, unabhängigcodiertesRTPS/PL-CDR-Paket gegen
  externenDecoderPASS; Syntax/diffPASS. Alle8Produktionshashes und generierten
  Messagebibliotheken unverändert; SDK70/ROS41 frühere volleValidation.
  KeineSDK-/ROS-C++-/Provideränderung, OwnedAnalysetoolContainer entfernt.

**Weiter:** KontrolliertenDDS-Discovery-Fragment-/Reliability-Verlust mitechten
Endpoint-/Callbackbeobachtungen undRecovery vorabfestlegen, erstdanach Default-
Änderungableiten. LängereSRT-N5ProgressCoverage separatvorabplanen. KeinLive-
Kausalnachweis oderN5/M3AbschlussinDieserAnalyse, PR2Draft, M4unberührt.


## Ergänzung 2026-11-08: kontrollierter nativer DDS-Fragmentverlust

GefrorenerPlan d12feb5, drei frühereBaseline-Fehler bleibenFAILED undFaultcases
jeweilsNOTEXECUTED; korrigierter5ba20c1Pair baseline+fragment-cutPASS. Nachweise:
[evidence/m3-dds-discovery-loss-2026-11-08/README.md](evidence/m3-dds-discovery-loss-2026-11-08/README.md).

- EigenständigerFastDDS-Probe, keinBridgeSDK/ROSCoordinator: UDPv4-only, festeOwned-
  Locator26010/26011, BE/Volatile/KeepLast1,10Hz, native28ByteHELLO. Robot-Pub/Sub
  user_data4096B erzwingtgroßeDiscovery;Operator leer. VerifiziertesN0/MTU1500,
  permanenteOwnedNeighbors, gemeinsameVMClock. KeineN5Shaper/Competitor/Sensorlast.
- DreiNoLossKontrollen matchen, habentrotzDATA0Callbacks. ZusätzlicheObserver
  zeigenReaderHistoryunread1 vorCallback/Codec. FixtureParticipantListener mit
  StatusMask::all fängtDATA_ON_READERS überleeregeerbteMethodeab; nativeMaske
  none lässtvendorDiscovery undReaderCallbacksarbeiten. KeineWire-/QoS-/Codec-
  oderProduktionsänderung. KeinBelegfüreinenidentischenROS/RMW-Fehler!
- KorrigierteBaseline echteCallbacks/Codec, Qualifier→Fence30/30; striktSteady29/28. Dannvor
  TeilnehmerstartgenauRobotUDPContinuationoffset185selektivgedroppt:18Packets/
  27252Bytes; VMhold8.000577254s, garantierterSelectorzeitraum9.638923087s.
  Participantdiscoverybeidseitiglive; Operator0Pub/SubMatches/0Callbacks, Robot
  1/1Matches und78Writes. AlleOperatorMatchbeobachtungenvorRestore unqualifiziert.
- NachHookRemovalQualifierSnapshots793.143250/804.947583ms (inklMatching,>=3Callbacks
  undStateSampling, keinepureDiscoveryLatency). OriginalePID/Start-/Participant/
  Writer/ReaderGUIDs bleiben;Restore→Fence33/33, strikt3sSteady28/29, invalid0.
- Paketidentitätenanderendecodergeprüft: baseline70, fault152 anbeidenTaps gleich.
  78RobotHELLOmitOriginsimHold/CutFensteranbeidenTaps, alleinOperatorPCAPorder
  vorersterkompletterRobotPublication(frame175). KeinRT-PCAPArrival-/Ageclaim.
  AlleFile/Filter/Kernel/Hash/Drain-PopulationenundNativeTrace/ShutdowngatesPASS.
- SeparateposthocFencedprüfung5606cdf schließtShutdown-Tailsaus, Originalresult.json
  unverändert. CLIslieferteninden3Fehlkohorten0trotzkorrekterFAILED-Matrix;
  künftigerCLI liefertbeiFailed/Skippednonzero, nurhostgetestet/keinealtenExits
  umgeschrieben. Host262PASS, StandaloneRelease/Werror/Syntax/diffPASS.
  NurFixtureELFneugebaut;alle8Produktionshashes gleich. SDK70/ROS41 früherevolle
  Validation, keinProduktionsbuild. AlleOwnedContainer/Netze/Selectorentfernt.

**Weiter:** ROS/N5-spezifischeDiscoveryMitigation/Bestätigung separatvorabplanen,
SRT-N5ProgressCoverageverlängern. DerkontrollierteMechanismusistbelegt, die
historischeROS/N5-Ursache/DDSdefaultnichtgefixt. KeinevolleN5/M3-/Hardware-/Clock/
Security-/ResourceAbnahme, keinacceptedCommandReplay. PR2Draft, M4unberührt.


## Ergänzung 2026-11-08: ROS-Transferprüfung und SRT-N5-Dreiseed-Progress

Gefrorener Source0641523, sechs Slots genau einmal, GesamtmatrixFAILED/Exit1.
Keine Retries; ROS/SRT unabhängige Gruppen. Evidenz:
[evidence/m3-ros-confirmation-srt-n5-2026-11-08/README.md](evidence/m3-ros-confirmation-srt-n5-2026-11-08/README.md).

- ROS system DDS N0/control-first Kontrollslot15s:8/8 bestätigte Commands,0Skip.
  Selektiver Fortsetzungsfragmentoffset185 vor Teilnehmerstart installiert;
  Faultslot12Drops/8656Bytes,8.002644087s Hold. Trotzdem beide Coordinator ready,
  alle vier Endpointzähler1, Operator HELLO83/82, Robot74/73. Vorabdefinierte
  Blockadehypothese widersprochen; FAILED, keine Recovery-Abnahme. Selektor
  entfernt, Restore-Barriere nie freigegeben, Workload nicht gestartet,0Execute,
  frische geschlossene Journals leer,11Typed-Snapshots jeRolle null. Alle drei
  nativen Kindprozesse sauber beendet. InternerStatus awaiting_recovery ist
  letzter geschriebener Schritt vor Assertion, kein erfolgreicher Recoverybeleg.
- N0 ohne Sensorlast/4096B Probe-Metadaten generalisiert den früheren nativen
  Verlustmechanismus nicht automatisch auf ROS/N5. Historische Loaded-Discovery-
  Ursache und Default-Mitigation bleiben offen; keine QoS-/Maskenänderung.
- SRT N0 Kontrollslot15s:8/8,0Skip. N5 je300s, Seeds1701/2903:131/131 bzw130/130
  bestätigt,19/20Skip. Seed4211:11/12 bestätigt,1unaufgelöst,138Skip. Originaler
  Safety/Accounting-HarnessPASS, strengere Progress-GateFAILED bleibt separat.
  Sensor Source/Observer:75028/7225,75030/12708,75034/27249; große Transportlücken
  ausdrücklich erhalten, keine volle Sensor-/N5-Qualifikation aus Command-PASS.
- Intent12 genau1SDK-Handoff,5sBudget unverändert. Live zuletztLOCAL_QUEUED/rev0,
  1337Polls/172NOT_FOUND-Beobachtungen; früherPeerclock_unqualified5, RequestKind
  nicht exponiert. Closed senderUNKNOWN/reconcile_required kann erstShutdown-
  Invalidation sein; keinLiveUNKNOWN beobachtet, ReceiverkeinEintrag. Keine
  Nichtausführungsaussage und keinReplay. KeineSession-/Invalidation-/Session-
  Action-/LinkLoss-Traceevents während aktivem Fenster. ReceiverTrace hatkeinen
  RequestAdmission-Punkt; fehlenderIntentTrace istkeinNichtempfangsnachweis.
- Alle Capturepopulationen/Trace-/Providerfooter vollständig. Beide tcpdump
  Listener vor Appstart bereit; kein AF_PACKET-Filter-before-bind-Claim.
  Host265 vor/nach LivePASS;8Produktionshashes gleich, keineProduktionsbuilds.
  SDK70/ROS41 bleibenfrühereValidierungen. PCAP/Journals/Provider-Rohsamples lokal
  gehasht, öffentliche Selektionen und ausgelasseneFelder explizitprovenant.
  OwnedContainer/Netze/Selektor entfernt, keineTests/Builds währendLivefenstern.

**Nächste Priorität:** SRT RequestKind und ReceiverAdmission-/Clock-Rejection-
Grenzen rein diagnostisch instrumentieren, gezieltenPlan einfrieren und die
4211-Lücke lokalisieren. Fehlerkontext ist bisher nicht eindeutig bestimmt.
Loaded ROS/N5-Discovery separat bestätigen; keineErfolgsretry-/Replay-/Expiryseal-
oderTimeoutänderung. N3/Clock/Security/Resources bleiben nachgeordnet.
PR2 bleibtDraft, M3offen, Intrinsic/M4unberührt.


## Ergänzung 2026-11-08: SRT-Admission-/Clock-Diagnostik

Source und Plan sind in b8f5418 eingefroren. Neue opt-in Beobachtungen erfassen
Transport-Admission (32), korrelierte Peer-Errors (33) und Receiver-Worker-Ergebnisse
(34), jeweils mit originalem COMMAND/QUERY-Kind und Sequenz. Admission erfasst
zusätzlich Origin, Evaluation, Clock-State/Deadline und AgeResult-Fehler. Die
bestehenden begrenzten SPSC-Lanes und Drop-Footer bleiben erhalten. Keine Änderung
an Replay, Clock-Policy, Budgets, Journal, Wire-Format oder Provider. Evidenz:
[evidence/m3-admission-diagnostics-2026-11-08/README.md](evidence/m3-admission-diagnostics-2026-11-08/README.md).

- Finaler Release-Build und vollständige Tests: SDK70/70, ROS41/41, Host267/267
  vor/nach Live PASS. Native IPv4/IPv6 prüfen erfolgreiche und negative Pfade,
  COMMAND-vs-QUERY-Fehler und kontrollierte Receiver-Clock-Expiry: Rejection13,
  Clock/Age expired2, Peer-Error5 mit derselben originalen COMMAND-Sequenz. Das
  validiert die Diagnose, nicht die historische N5-Ursache. Der erste Build wurde
  für die AgeResult-Ergänzung abgebrochen (137); sein Partiallog zählt nicht als
  erfolgreiche Validation. Der finale Source wurde neu gebaut und voll getestet.
- Zwei Slots genau einmal: N0/4211/15s bestätigt8/8,0Skip; N5/4211/300s
  bestätigt124/124,26Skip,0unaufgelöst. Jeder Erfolg hat passende geschlossene
  Journals, originales5sBudget, rechtzeitigen Dispatch, genau einen SDK-Handoff
  und neue Receiver-Admission-/Worker-Beobachtungen. Receiver32/34 zählen19/19
  bzw1006/1006 inklusive QUERY. Keine Drops, Peer-Errors, Receiver-Clock-Rejections
  oder aktiven Kontextwechsel-Ereignisse.
- Neuer Intent7 wurde vor dem SDK wegen Clock-Qualification gehalten:957.679ms
  bis zu genau einem SDK-Handoff, danach qualifizierte Receiver-Admission und
  dauerhafter Erfolg mit originalem Budget. Das übt bestehende Unsent-Retention
  aus; kein Replay und keine Recovery des alten Intent12.
- Der historische4211-Stall wurde nicht reproduziert und bleibt ungelöst. Alte
  FAILED-Matrix und UNKNOWN-/NOT_FOUND-Ungewissheit bleiben unverändert; keine
  Nichtausführungsbehauptung. Sensor Source/Observer75036/19012 enthält weiterhin
  explizite Lücken; keine volle Sensor-/N5-Abnahme.
- Capture-Populationen, Drain und Trace-/Provider-Footer PASS. Nur bridge_node,
  endpoint.a und transport.a änderten sich gegenüber der alten Runtime. Alle acht
  Hashes bleiben während/nach Live gleich, Provider-Pin unverändert. Keine Tests
  oder Builds während Live; eigene Namespaces entfernt. Rohdaten bleiben lokal
  gehasht; öffentliche Selektionen und normalisierte Host-Displaylogs haben
  explizite Provenienz.

Weiter: Gezielte Receiver-Clock-/Future-Age-Rejection-Coverage samt Unsicherheits-
semantik vorab festlegen, danach eine begründete endliche instrumentierte
Mehrseed-Cohort. Keine Deadlineverlängerung und keinen Nonrecurrence-PASS als Fix
werten. Loaded ROS/N5-Discovery bleibt separat, N3/Clock/Security/Resources folgen.
PR2 bleibt Draft, M3 offen, Intrinsic/M4 unberührt.


## Ergänzung 2026-11-08: kontrollierte Clock-Rejection und Ungewissheit

Plan c9398eb, vollständige SDK-Validation deedc54:71/71 PASS, Host267/267 PASS.
Nur Test-/Build-Testregistrierung geändert, keine Produktionsalgorithmen oder
Runtime-Installation. Evidenz:
[evidence/m3-controlled-clock-rejection-2026-11-08/README.md](evidence/m3-controlled-clock-rejection-2026-11-08/README.md).

- Neuer direkter Session-/Journal-Vertrag: Fresh-Control akzeptiert; Receiver-
  Clock-Expiry liefert SessionError13/AgeError2/ClockState2, Future-Age liefert
  13/9/0. Future-Case nutzt explizite logische Zeiten mit200ms Sender-Vorsprung
  nach Zero-Offset-Qualifikation; keine Hostclock-/SRT-/ROS-Manipulation. Beide
  Negativfälle behalten CONTROL, konsumieren die Replay-Watermark und erlauben
  QUERY. Budgetablauf/NOT_FOUND erzeugen kein negatives Ergebnis oder neues
  Budget. Reopen bleibt UNKNOWN/reconcile_required ohne Senderecht.
- Echte native SRT IPv4/IPv6 je einmal: Receiver-Testdeadline150ms bei1sProbes,
  COMMAND-Rejection/PeerError mit originaler Sequenz korreliert. QUERY vor/nach
  originalem5sBudget liefert lokal LOCAL_QUEUED und Peer NOT_FOUND ohne Result.
  Receiver-Restart mit normaler Qualification lässt den lebenden Sender zu
  UNKNOWN/reconcile_required wechseln. Existing-ID-Execute reconciliert nur;
  genau1SDK-Handoff insgesamt, keine Trace-Drops, beobachtete Fixture-Effects0.
- Vier geschlossene Journalpaare read-only geprüft: Sender UNKNOWN/rev0/kein
  Result/originales5sBudget, Receiver leer. Kein Nichtausführungsbeweis aus
  Abwesenheit und keine Replay-Freigabe. Historischer4211-Stall bleibt ungelöst.
- Nach erfolgreicher Suite wurde nur die Ausgabeallokation des neuen direkten
  Protokolltests von PID auf mkdtemp gehärtet (9e174d5). Dieser nichtnetzwerkende
  Vertrag wurde einmal gezielt neu gebaut/geprüft. Ursprüngliche71er-Suite und
  separate Revision behalten eigene Source-/Binary-/Log-Provenienz; keine native
  Fehlersuche erneut ausgeführt. Alle8 Runtimehashes/Providerpin unverändert,
  keine ROS-Neuvalidation (vorherige41), eigene Container entfernt.

Weiter: Endliche instrumentierte Mehrseed-N5-Cohort vorab festlegen, um eine
request-korrelierte Wiederkehr zu untersuchen; keine Deadlineänderung, kein
Replay oder Retry bis PASS. Loaded ROS/N5-Discovery bleibt separat, ebenso die
weiteren N3/Clock/Security/Resource-Gates. PR2 Draft, M3 offen, M4 unberührt.


## Ergänzung 2026-11-08: request-korrelierte N5-Wiederkehr

Matrix/Source a2425d0 vorab eingefroren: N0/4211/15s, dann N5 je300s mit Seeds
4211,1701,2903; Stop nach erstem Fehler, keine Retries. N0 bestätigt8/8. N5/4211
bestätigt18/19,1unaufgelöst,131Skip; Progress-GateFAILED/Exit1, ursprünglicher
Safety/Accounting-HarnessPASS unverändert. Seeds1701/2903 NOT_EXECUTED. Evidenz:
[evidence/m3-instrumented-n5-matrix-2026-11-08/README.md](evidence/m3-instrumented-n5-matrix-2026-11-08/README.md).

- Intent19 genau1SDK-Handoff. Receiver COMMAND-Rejection13 mit ClockError2 und
  AgeResult2 (expired), Sender COMMAND-PeerError5; Request/Session/Route100 und
  Originalsequenz152 passen exakt. Keine QUERY-Verwechslung oder Future-Age-
  Rejection in diesem beobachteten Fall. Transport verwirft vor Worker-Forwarding;
  kein COMMAND-WorkerResult, spätere QUERYs liefern NOT_FOUND. Warum die Clock-
  Qualification unter dieser Last abläuft, ist weiterhin nicht lokalisiert.
- Shared-VM-Vergleich:2.807178502s von Originalorigin bis Receiver-Evaluation,
  dabei2.192821498s des originalen5sBudgets übrig. Keine PCAP-/Crosshost-Age-
  Garantie. Clockdeadline0 im expired-Snapshot bedeutet nicht verfügbar, nicht
  den tatsächlichen Ablaufzeitpunkt. Keine aktiven Kontextwechsel-Traceevents.
- Ein späterer QUERY-Snapshot zeigt Qualification192.868500ms nach Rejection und
  noch1.999952998s Budget. Das ist eine Stichprobe, keine genaue Recovery-Latenz
  und kein Beweis für hypothetischen Fix-Erfolg; QUERY-AgeError1 ist ungenutzt.
- Live zuletzt LOCAL_QUEUED/rev0,1263Polls/150NOT_FOUND-Beobachtungen,1199
  historische Polls ausgelassen. Closed senderUNKNOWN/reconcile_required kann
  Cleanup-Invaliderung sein; kein Live-UNKNOWN daraus abgeleitet. Receiver leer,
  kein Result. Keine Replay-/Nichtausführungsfreigabe aus Logs/NOT_FOUND/Deadline.
- Capture-/Drain-/Trace-/Provider-Populationen PASS, Drops0. Jeder bestätigte
  Erfolg hat genau ein originalkontextgebundenes Admission-/Worker-Paar zusätzlich
  zu den Journal-/Dispatch-/Budget-/SDK-Beweisen. Neue negative Hosttests prüfen
  falsche Session/Route/Origin/Sequenz und doppelte Beweispopulationen.
- Host269 vor/nach LivePASS, Syntax/diffPASS. Alle8 Runtimehashes entsprechen der
  vorherigen Diagnostic-Runtime und bleiben unverändert; Providerpin gleich.
  Kein SDK-/ROS-Build (vorher SDK71/ROS41), keine Tests während Live, eigene
  Namespaces entfernt. Sensor Source/Observer75032/24417 mit expliziten Lücken;
  keine volle N5-/Sensor-/M3-Abnahme. Rohdaten lokal gehasht, Selektionen mit
  dokumentierten Auslassungen und Original-/Ableitungshashes archiviert.

Weiter: Begrenzte Receiver-Retention während temporärer Clock-Gaps entwerfen und
separat vorab testen, gebunden an Originalcommand/-kontext/-deadline, einmaliges
Forwarding ohne Sender-Replay. Spätes Expiry, Kontextverlust, Kapazität und Shutdown
explizit abdecken; keine flüchtige Rejection zum dauerhaften Absence-Seal erklären.
Underlying Clock-Ablauf und historische Ursachen bleiben getrennt. Loaded ROS/N5-
Discovery separat; PR2 bleibt Draft, M3 offen, Intrinsic/M4 unberührt.


## Ergänzung 2026-11-08: begrenzte Receiver-Retention

Plan f9101a1, Build-/Live-Source4a510e7. Der Transport hält jetzt nach struktureller,
Identitäts-, Payload- und Sequenzprüfung soft-clock-unqualifizierte COMMANDs in
festem FIFO. Originalframe/-kontext/-timestamp/-budget bleiben unverändert;
Session::check_command revalidiert vor einmaligem Forwarding, kein SRT-Replay.
Future-/Hard-Errors ausgeschlossen. Ready+retained <=64, COMMANDs <=56,8Slots für
andere CONTROL-Nachrichten,8 Revalidierungen pro Loop. Kapazität wirft älteres
Work nicht weg; Kontextverlust/Shutdown räumen auf. Lokales Hold-Ceiling ist nur
Ressourcenschutz, kein neues Ausführungsbudget. Evidenz:
[evidence/m3-receiver-clock-retention-2026-11-08/README.md](evidence/m3-receiver-clock-retention-2026-11-08/README.md).

- Neue Tracepunkte35/36/37/38 unterscheiden Defer/Resume/Drop/Capacity. Audit bindet
  frische Revalidation an Originalrequest/-kontext/-origin/-sequenz und zählt
  initiales Gate nicht doppelt. control_received enthält Ready+Retained. Fester
  zusätzlicher Speicher für56Frames; kein Overhead-Äquivalenzclaim.
- Release/Werror SDK72/72, ROS41/41, Host271 vor/nach LivePASS. IPv4/IPv6 jeweils
  Recovery mit originalem5sBudget:1SDKHandoff/1Forward/1Effect/ClosedSuccess.
  Negative Original500ms-Fixtureexpiry, CONTROL-Verlust und Shutdown: je1Handoff,
  0Forward/Effect, ClosedUNKNOWN ohne Result. Acht geschlossene Journalpaare und
  Tracepopulationen ohne Drops geprüft. FIFO-/Kapazitäts-/Kontext-/Future-/Hard-
  Grenzen und frische Requalification nach ursprünglichem Deadlineablauf geprüft.
- Zwei vorab geplante Live-Slots genau einmal: N0/4211/15s8/8,0Skip; N5/4211/300s
  21/22 bestätigt,1unaufgelöst,128Skip. CandidateProgressFAILED/Exit1; ursprünglicher
  Safety/Accounting-HarnessPASS bleibt. Keine Zusatzseeds/Retry.
- Intent22 kommt bei initialer Receiver-Evaluation10.159390588s nach Origin an,
  schon5.159390588s nach originalem5sSenderdeadline (SharedVM-Vergleich, kein
  reiner Wire-/Networkdelayclaim). Clockexpired2 führt zu Retention, frische
  Requalification liefert stale_sample25; Drop nach274.626125ms Traceabstand,
  matched COMMAND START_EXPIRED6/Originalsequenz155. Kein Resume/WorkerForwarding.
  Das ist sicheres Nichtstarten eines verspäteten Frames, kein Beleg, dass ein
  hypothetischer Fix in einem früheren Lauf funktioniert hätte.
- START_EXPIRED bleibt flüchtige Diagnose, kein dauerhafter Terminalstatus. Live
  zuletztLOCAL_QUEUED/rev0,1252Polls/135NOT_FOUND-Beobachtungen,1188 ausgelassen.
  ClosedUNKNOWN kann Cleanup sein, Receiver leer; keine Replay-/negative Outcome-
  Freigabe. Kein aktiver Kontextverlust. Sensor Source/Observer75030/17058 enthält
  große Lücken; volle N5-/Sensor-/M3-Abnahme bleibt offen.
- Capture/Drain/Trace/Provider-Gates PASS; jeder bestätigte Erfolg mit Original-
  Budget-/Dispatch-/Journal-/einmaligemSDK-Beweis. Nur bridge_node/transport.a neu;
  alle8 rebuilt Runtimehashes während/nach Live gleich, Providerpin unverändert.
  Keine Builds/Tests während Live, eigene Namespaces entfernt. Rohdaten lokal
  gehasht, öffentliche Selektionen und Auslassungen explizit dokumentiert.

Weiter: Dauerhaften Receiver-Expiry-Status für vollständig validierte und mit
qualifizierter Clock beweisbar veraltete Commands entwerfen, ohne Dispatch,
Replay, Deadlineerneuerung oder Absence-Erfindung. Bei fehlendem Clock-/Kontext-
Beweis UNKNOWN bewahren. Terminal-Progress getrennt von All-Success-Deadlinegate
führen; ursprüngliche FAILED-Verdikte nicht umwerten. CONTROL-Verzögerung/Clock-
Expiry-Ursache separat untersuchen. PR2 bleibt Draft, M3 offen, M4 unberührt.


## Ergänzung 2026-11-08: dauerhafter Receiver-Expiry-Status

Plan1f11963, Build-/Live-Sourcea866505. Vollständig validierte empfangene Commands
können jetzt EXPIRED/start_deadline dauerhaft journalisieren, wenn eine qualifizierte
AgeResult-Untergrenze strikt über dem Originalbudget liegt. Obere Grenze allein
oder ein straddling Intervall genügt nicht. Latest-Deadline = Evaluation minus
(lower_age-budget), positiv und bereits vergangen. Diese Evidenz ist kein neues
Ausführungsfenster. Interner expiry_only-Pfad darf niemals dispatchen, sendet erst
nach Commit STATUS und lässt bestehende Records maßgeblich. Kein neues Wireformat,
Provider-/Clock-Config-Wechsel, Replay oder Deadlineerneuerung. Fehlender Beweis
bleibt ungewiss. Evidenz:
[evidence/m3-durable-receiver-expiry-2026-11-08/README.md](evidence/m3-durable-receiver-expiry-2026-11-08/README.md).

- Sowohl initial qualifiziert verspäteter Empfang als auch retained Revalidation
  nutzen denselben Beweis. Straddling darf begrenzt warten; zukünftige/ungültige/
  unqualifizierte Clock, NOT_FOUND, Timeout, Abwesenheit und Underflow beweisen
  keine Expiry. Neuer Trace39 hält Originalkontext/-sequenz, lower/upper-Age,
  Originalbudget und Latest-Deadline fest. Worker34 und geschlossene Journals
  validieren den Commit unabhängig; Logs allein schaffen keine Autorität.
- Release/Werror SDK72/72, ROS41/41, Host273 vor/nach LivePASS. Vier echte native
  IPv4/IPv6-Delayfälle (Original500ms-Budget,650ms CONTROL-Gate): direct und
  retained Latearrival jeweils1SDK-Handoff/0Dispatch/0Effect, ClosedEXPIRED ohne
  Resultpayload, echter QUERY nach Receiver-Restart und Duplicate-ID ohne Replay;
  späterer frischer IntentSUCCEEDED. Acht frühere Retention-Negative/Recovery-Cases
  bleiben grün. Beweisschwellen/Equality/Straddle/Invalid/Future/Underflow geprüft.
- Zwei geplante Live-Slots genau einmal: N0/4211/15s8/8; N5/4211/300s136/136
  bestätigt,14Skip,0expired/0unaufgelöst. Sowohl striktes All-Success als auch
  explizites neues Success-or-Verified-Expiry-CompletionPASS, Exit0. Keine echte
  Live-Expiry in diesem Lauf; native Abdeckung nicht als Livebeweis ausgeben.
  Default-All-Success unverändert, alte FAILED-Matrizen/UNKNOWNs nicht umgewertet.
- Neuer LiveIntent5 hält senderseitig vor SDK (Traceabstand2.235969917s), dann
  receiverseitig604.138208ms; Originalorigin bis frischer Receiver-Evaluation
  2.860698626s, Ageintervall[2.851650879,2.883293135]s innerhalb5s. Genau1SDK-
  Handoff,1Resume, rechtzeitigerDispatch und dauerhafterSuccess. Keine genaue
  Clock-Recovery-/Wire-Latenz oder Gegenbeweis zu einem historischen Fehler.
- Telemetrie bleibt schlecht: Source75022/Observer871, größte Kategorie71187
  SRT-Accept-to-Receiver-Gap; alle sechs Residuen0, Source~200/50Hz. Keine eindeutige
  physische Loss-/Providerursache und keine volle Sensor-/N5-Abnahme daraus.
- Capture/Drain/Provider/Trace-Populationen PASS, Drops0, keine aktiven Kontext-
  wechselereignisse. Alle Successes mit passenden Journal-/Budget-/Dispatch-/
  Originalkontext-/Sequenz-/einmaligemSDK-Beweisen. Rebuilt bridge_node,
  dds_command_node, endpoint.a, transport.a (auch gemeinsames Code/Header-Relinking);
  alle8 Hashes während/nach Live fest, Providerpin unverändert. Kein DDS-Profil-
  oder Defaultwechsel/neue DDS-N5-Qualifikation. Keine Tests/Builds während Live,
  eigene Namespaces entfernt. Rohdaten lokal gehasht, Selektionen dokumentiert.

Weiter: Breitere vorab fixierte instrumentierte N5-Seed-Abdeckung mit getrennten
All-Success-/Verified-Expiry-Completion-Verdikten. Sensorverfügbarkeit separat
untersuchen. Historische UNKNOWNs nicht rückwirkend ablaufen lassen; keine
Budgetlockerung, kein Retry bis PASS. FullM3/LoadedROSDiscovery/Hardware-/Clock-/
Security-/Resource-Gates bleiben offen, PR2 Draft, Intrinsic/M4 unberührt.

### 2026-11-08 — Weitere N5-Seeds und Telemetrie-Diagnose

- Evidenz: `evidence/m3-broader-seeds-telemetry-2026-11-08/README.md`.
  Vorab fixierte Slots einmalig: N0/1701/15s8/8; N5/1701/300s125/125,25Skip;
  N5/2903/300s97/98,52Skip,1unaufgelöst. Beide Command-Gates FAIL für2903,
  CohortExit1,0verifiedExpiry. Separate vorherige4211-Kohorte bleibt136/136,
  14Skip. Kein Retry/Umwerten/Defaultwechsel; Runtime8Hashes gleich der4211-Kohorte.
- Intent98: genau1SDK-Handoff, Senderstate8/reason2/rev0, kein Receiverrecord und
  kein originaler COMMAND-Admission-/Retention-/Expiry-Trace. Danach CONTROL-
  Linkverlust/Sessioninvalidierung, neue Session/QUERY mit NOT_FOUND. Keine
  Nichtausführung oder nachträgliche Expiry daraus ableiten, keinen Replay.
- Geschlossene Originalcaptures aller5Vergleichsfälle: alle Rotationen/Footer/
  Populationen vollständig, exakt gleiche UDPtuple+Payloadhash-Multimengen in
  beiden Richtungen. Kein Beweis gegen Pretaploss. Root/Child-Drops spiegeln
  sich: nie summieren. Robotrootdrops4211/1701/2903=2716297/116533/166531;
  Operator0/0/396. Konkurrent tatsächlich128Kbit/s UDP, TBF512kbit/s, Childlimit16.
- Source/Observer N5: vorher4211=75022/871, neu1701=75037/27890,
  neu2903=75023/26465. Accept-to-Receiver-Gap71187/43674/42255, alle6Residuen0,
  Source~200/50Hz. Observerwerte sind keine Provider- oder Sensorabnahme.
- Wholecapture SENSOR-DROP_REQUEST39761/670/3201, davon7837/346/2211Repeats.
  Keine DATA nach vorherigem Retirement derselben Sequenz im Capture-Dateiorder;
  Overtakinghypothese nicht beobachtet. Später benannte DATA9673/122/317,
  ohne Beweis für angewandte Retirements/unread-buffer-Verlust. Provider52be7c8
  read-only: bounded10ms/32Prefix-Retrymechanismus plausibel für Feedbackdruck,
  nicht eindeutig nachgewiesene Ursache. SENSOR-Insertion/Delivery-/Decrypt-/
  Retirement-Innenzustände und verschlüsselte SAMPLE-Zuordnung fehlen weiterhin.
- FrozenLiveSourceabc0ebb; nach geschlossenem Archiv separater PosthocAnalyzer
  04c163b,4Tests. Host278 vor Live/282 nachherPASS; SDK72/ROS41 bleiben vorherige
  Validierung, kein neuer Build. Keine Tests/Analyse/Builds während Live. Eigene
  Namespaces/Passphrase entfernt, Rawhashes/selektierte öffentliche Artefakte und
  Auslassungen dokumentiert. Fehlender falscher N0-Analyserpfad als failed erhalten,
  nur read-only mit korrektem Pfad korrigiert, kein Livererun.

Weiter: Separaten begrenzten Diagnoseplan einfrieren: zuerst2903 CONTROL/Session
mit Kernelmonotonic-/Providercorrelation, separat SENSOR-Provider-Insertion,
Delivery/Retirement/Decrypt sichtbar machen. Erst danach kontrollierte Pacing/
Latestdata-Gegenprobe, keine Kausalbehauptung aus Packetcounts. Originalbudgets,
beide Gates und historische Unsicherheit erhalten. FullM3/N5/LoadedROSDiscovery/
Clock/Security/Resource/Hardware weiter offen, PR2 Draft, Intrinsic/M4 unberührt.

### 2026-11-08 — Session2903 reproduziert, SENSOR-Provider sichtbar

- Evidenz: `evidence/m3-session-sensor-visibility-2026-11-08/README.md`.
  Plan830e427, Implementierung2810996, Fixturekorrektur/Analysea20f1ce,
  finaler Python-Driver/Livefreeze03ffa03. Einmalig N0/2903/15s8/8,0Skip;
  instrumentiertes N5/2903/300s11/12,138Skip,1unaufgelöst, beide GatesFAIL,
  CohortExit1. Kein Retry/Expiry/Replay; Originalintent98 weiter unaufgelöst.
- Neuer Intent12 genau1SDK-Handoff, Senderstate8/reason2/rev0, kein Receiverrecord
  oder originaler COMMAND-Admission-/Retention-/Expiry-Trace. Neue Beobachterlast
  und andere Intentnummer: gleiche Fehlerklasse, keine eindeutige historische Ursache.
- Matched CONTROL operator→robot: nativequiet5004643627ns bis Robotlinkverlust,
  tatsächliches Peeridle5000ms. In47vollständig enthaltenen Providermesspaaren
  SenderDATA+309/retrans+292/ACK+42/NAK+1, aber0Source-/0Peertapbeobachtungen
  dieser alten Flowidentität. Erfolgreiche UDP-Submission liegt laut Providercode
  vor dem Counterincrement. Lokalisation daher Sendercompletion→Sourcehook,
  nicht eindeutiger Provider-/Kernel-/Qdisc-/Neighborgrund. Gesamter Sourcegap
  5.263612877s. Operatorloss15.736125ms später, vorher Shutdown; zweite Mapping-
  Assoziation korrekt withheld, kein unabhängiger Idlebeweis.
- Nach Sender-BROKEN-Beforeclose und No-socket-Sample weitere4DATA/2ACK der alten
  Flowidentität an beiden Hooks. Kein neuer SDKCOMMAND-Handoff/Replaybeweis;
  genaue Close-Drain-/Kernelqueue-/Neighbor-/Qdiscursache noch offen.
- Separate default-off SENSOR-Stats:128SPSC/75000Cap/100ms/Beforeclose, eigene
  Footer/Channel/Schema/Unavailable-/Saturation-/Reset-Gates. Bestehendes bstats
  liefert DATA/Unique/Loss/Drop/Undecrypt/FEC und geglättete Buffer/Flowgauges.
  Kein Dependencyedit. Fehlende Insertion-/Retirement-/Delivery-Reasonfelder
  explizit unavailable, Counter überlappen und sind keine exklusiven Lossklassen.
- N5 Source75036/SDKaccepted70889/Decoded8265/Observer7704; Gap62624,Reject559,
  UnknownAge530/Stale0,6Residuen0,~200/50Hz. Nach Reconnect SENSORflow:20471
  eindeutige DATA an Operator,0Retrans, ProviderDATA20832/FilterExtra361,
  Unique5421inkl.FEC,Drop8272/Undecrypt0. Provider-Akzeptanz/Window statt nur
  Bridgefreshness weiter eingrenzen; kein genauer Ablehnungsgrund oder SDKbugbeweis.
- Initiale native Fixtureverwechslung available=connected:70/72,2Fehler erhalten,
  kein Install/ROS/Live danach. Korrigiert SDK72/ROS41/Host296PASS. Verfügbare
  Stats können BROKEN sein; Status unverändert erhalten. Rebuilt bridge_node,
  endpoint.a,transport.a;8Runtime+2ObserverHashes fest, Provider unverändert.
  Keine Builds/Tests/heavyAnalyse während Live; Cleanup/Rawhashes/SelektionenPASS.
  Ein Syntaxfehler in ad-hoc Posthocimport als Vorbereitung erhalten, kein Livererun.

Weiter: Separaten begrenzten UDP-/Neighbor-/CONTROL-Qdisc-Beobachterplan mit
Monotonic und ARP-/Neighbornachweis einfrieren, dynamische Nachbarn beibehalten,
Originalbudgets/Idlewerte nicht lockern. Danach Review einer upstreamfähigen
SENSOR-Insertion-/Retirement-Reasonoberfläche; .deps nicht direkt ändern. Kein
FullM3/N5/DefaultDDSDiscovery-/Clock/Security/Resource/Hardware-/Superioritätsgate
geschlossen. PR2 Draft, Intrinsic/M4 unberührt.

### 2026-11-08 — UDP/Neighbor/Qdisc-Stufen getrennt, kein Tuning

- Evidenz: `evidence/m3-udp-neighbor-qdisc-2026-11-08/README.md`.
  Plan68d7297, Livefreeze b9aaf03. Einmalig N0/2903/15s8/8,0Skip;
  N5/2903/300s126/126,24Skip,0expired/unaufgelöst, beide GatesPASS,Exit0,
  0aktive Kontext-/Linkereignisse. Zusätzliche Beobachterlast: keine Fehlerbehebung
  bewiesen, alte Intents98/12 bleiben unaufgelöst. Kein Retry oder Tuning.
- Bestehender ETH_P_ALL-Nativrecorder enthielt bereits ARP. Vorherige Fehlerkohorte
  hash-guarded reanalysiert:5Requests/5reflektierte lokale Kopien,0Peerreply im
  5.0046s-Lossfenster; im einschließenden5.2636s-Gap6Requests+1späteAntwort,
  gefolgt von alter Flowegress5.416us später. Keine damaligen Neighbor-/TC-Samples
  nachträglich erfinden. MAC/IP-Richtung verhindert das Zählen lokaler Spiegel
  als Peerreply; ARPpräsenz ist keine authentifizierte Neighborannahme.
- Neue Beobachtung dynamischer Neighbor100ms und CONTROL SoftwarePASS/Root200ms,
  beide Providerstreams/Commandtrace/Nativev2/PCAPdrain. N0positiv240/250PASS-
  Increments und vollständige Populationen; Rootoptionen bleiben erhalten.
- 4prospektive>=1s-Sourcegaps, keine Losswindows. Operator1.528s: DATA+91/retrans75,
  PASS0, Rootdrops0/qlen0, NeighborPROBE4/INCOMPLETE11. Common-read-Witness zwischen
  Filterbrackets mit12vollständig enthaltenen Providerpaaren:75DATA/59retrans/
  20ACK, weiterPASS0/Bytes0 und0SourceCONTROLhooks. PeerARP-Antwort vor erneutem
  Egress53.541us. Lokalisation vor gewählter PASS-Ausführung mit Neighborlead,
  kein eindeutiger Kernelgrund oder exakter Zustandsübergang.
- Robot1.332s:PASS30,Rootdrops1390,qlen16, gemischtePROBE/INCOMPLETE/REACHABLE-
  Samples. Robot1.349s:PASS20,Rootdrops9491,qlen16,DELAY14,keinARPimFenster,
  kein ausgewählter SourceCONTROLhook. Damit auch Stufe nach PASS/Rootdruck;
  nicht alle Gaps sind Neighborauflösung. Operator1.002s ohne Providerincrement
  bleibt ausdrücklich kein Lossbeweis. Rootstats betreffen ganzes Interface,
  Spiegel-Child nicht summieren; keine individuelle Paketdropzuordnung.
- N5 Source75033/SDKaccepted71310/Decoded9708/Observer8640,Gap61602,Reject1067,
 6Residuen0,~200/50Hz. Keine Sensor-/FullN5/M3-Abnahme. PCAPmultisets74749/66131
  beide Richtungen identisch, Native/Provider/Neighbor/TC/TracepopulationenPASS.
- Host301 vor Live; erste Fixturealias-Verwechslung /var vs/private/var als1Fehler
  erhalten, vor Live korrigiert. Nach geschlossenem Sourcearchiv Posthoc-Witness
 4c1e113 mit5Grenz-/Unavailable-/Identity-/Regressionsguards, Host306PASS.
  Kein neuer SDK/ROS/Recorderbuild:72/41 frühere Validierung.8Runtime+2Observer-
  Hashes gleich vorher/fest, Provider unverändert, keine Tests/Builds/heavyAnalyse
  während Live. Rule/eigene Namespaces/Credentials entfernt. Vollständige öffentliche
  Rawfile-Disposition plus Selektionsfelder/Hashes dokumentiert.

Weiter: Separat qualifizierter ARP-PASS-/Preqdisc-Beobachter und kontrollierter
ARP-Replylossfall, getrennt vom bekannten CONTROL-Rootlosskontrollfall. So erst
ARP-Replygenerierung gegen Rootqueue/Drop abgrenzen; dynamische Defaults,Original-
Budget/Idle unverändert lassen. Bisher nur Stufenassoziation, keine eindeutige
historische Ursache. Alle übrigen M3/DDSDiscovery/Clock/Security/Resource/Hardware-
und Vergleichsgates offen, PR2 Draft, Intrinsic/M4 unberührt.

### 2026-11-08 — Kontrollierter Kernel-ARP-Replyloss, kein Tuning

- Evidenz: `evidence/m3-controlled-arp-reply-loss-2026-11-08/README.md`.
  Plan20d8a38, V1Source38a6f0a; neue scoped V2Source770632a. Reine synthetische
  UDP-/KernelARP-Fälle in frischen eigenen Namespaces, kein ROS/SRT/N5-Lauf.
- 3Zero-Traffic-Vorbereitungen erhalten: flower nicht vorhanden→FAILED; u32install
  klappt, JSONreadback verliert wiederholte match-Keys→FAILED; korrigierter
  object-pairs-Parser erhält7ARP-Payloadwörter, exakter Software-u32/PIPE→DROP-
  Readback undRemovalPASS. Keine ARP-/UDP-Probes in diesen3Namespaces.
- V1Clean einmal ausgeführt, FAILED wegen breiter Native/PCAP-ARP-Identitätsgate:
  extraPCAP-GARP mitSenderIP==TargetIP; eindeutiger One-recorder-Grund nicht
  bewiesen. V1Replyloss NOT_EXECUTED. Source/Rawhashes vor Revision verifiziert;
  nichts rückwirkend reparieren oder als akzeptierten Control ausgeben.
- PLAN-V2 vor neuen Slots: Identitäten zwischenownedPeerIPs (ARP1/2) plus alle
  gelabeltenUDP prüfen; kompletteNative/File/Filter/Kernel-Populationen weiter
  strikt. Alle anderen ARPs separat mitBackgroundtabellen/Equality erhalten.
  V2 beideSlots einmaligPASS: Clean1eligible/0drop,1Reply an beidenTaps;
  Fault2eligible/2drop (84bytes),0Reply und0originalUDP während aktivemFault.
- gactPIPE zählt vor gactPASS/DROP derselbenRule, kein terminalerPASS vorDROP.
  Exact7-wordARPselectorOp2/SHA/SPA/THA/TPA; EthernetMAC/IP/Richtung separatnative
  verifiziert. Kernel erzeugt Replies; kein UserspaceARPsender. BeideController-
  Snapshots stabil, Rule danachleer. N0Roots identisch,Rootdrops0; keineRate/
  Queue/Sysctl/Idle/Budget/Neighbordefaultänderung, keinPing/Flush/Permanententry.
- FaultRemoval beginnt1.350737001s und endet1.368607751s nacherstemSend. Nächster
  echterPeerreply danach;3originale1200ByteUDP-IDs treten erst~2.0633s nachSend
  auf und kommen jeweils1x an, ohneSourceResend. ExtraCase1002/Seq0 alsfrischer
  Control1x. Sourcehook4.083us nachPeerreplyhook: lokalerFixturebezug, keine
  generelleLatenz-/Physical-Wire-Garantie oder SRTCommandauthority.
- Operator20INCOMPLETE-Samples, später4REACHABLE; frischePeers initialABSENT,
  Robot nachLearningSTALE. BekannteRepliesgenerierung gegen kontrolliertenDrop
  vorAF_PACKET qualifiziert; organischeN5Rootqueue-/ARP-Ursache bleibtunbewiesen.
- V2PCAPPopulationenClean10/9,Fault14/11,alleCaptured/File/Filtergleich0Kernel-
  Drops; Nativevollständig0Reserve/Copyloss, ownedPeerMultisets/PayloadhashesPASS.
  Host316vorV1/317vorV2.8Runtime+2ObserverHashes gleichvorher/fest; Provider
  unverändert, keinSDK/ROS/Recorderbuild (72/41 frühereValidierung). KeineTests/
  Builds/heavyAnalysewährendLive. Controller/Receiverexit0,keineForcedkills,
  alle6eigenenNetze/Container/Credentials entfernt,309Rawfiles gehasht/Selektion
  explizit. EinfalscherFooterkey in read-onlyConsolekorrektur ändertekeinenLauf.

Weiter: Separaten geladenenN5-ARP-Preqdisc-Counterplan einfrieren; qualifizierten
PIPE-Zähler nutzen, um Replyeligibilität gegen spätereQueue/Drop-Assoziation unter
Last zu trennen. NochkeineDefault-Tunings oderhistorischeAuflösung. AlteIntents98/
12, FullM3/N5/DDSDiscovery/Clock/Security/Resource/Hardware-/Vergleichsgates offen,
PR2 Draft, Intrinsic/M4 unberührt.

### 2026-11-09 — Loaded ARP reply eligibility, no tuning

- Evidence: `evidence/m3-loaded-arp-eligibility-2026-11-09/README.md`.
  Plan24062a9, frozen live source2aae62b. PASS-only exact seven-word ARP reply
  selectors on both peers,200ms/37500-record polling; separate CONTROL preference.
  Every read validates software selector/actions/indexes/zero drops. Non-atomic
  PIPE/PASS counters are not exclusive drop buckets. Dynamic defaults unchanged.
- Once each: N0/2903/15s8/8,0skips; N5/2903/300s134/134,16skips,zero expired/
  unresolved/context-loss, both command gatesPASS/exit0. No retry or resolution
  of prior intents98/12. Added observer work prevents a mitigation claim.
- N0 reply counts operator1/robot2; N5 lifetime execution counts11/14. Primary
  selection finds one1.026943917s robot CONTROL gap with10INCOMPLETE samples;
  contained responder reads have no positive growth, but the next read includes
  the late edge reply. Zero growth is not generation-absence proof.
- After closed source verification:17e4e46 adds correct responder-root scope and
  two tests;051df30 separately audits ALL positive reply steps in publication.
  Operator10steps have replies; robot13steps have5with/8without source replies
  in~222–224ms outer envelopes. Each missing envelope reports+1PIPE/+1PASS,
  zero action drops. These are eight windows, not eight lost packets; later
  observations may fall outside and ARP has no request nonce.
- All eight have wider~645–647ms robot-root context with drops176..6089 and
  sampled peak qlen16, requester DELAY/PROBE. Whole-interface root context is
  not specific ARP loss. Post-eligibility absence/delay localized, exact branch
  and historical cause unproved; no tuning.
- Source75034/SDKaccepted72066/decoded15913/observer15850; gap56153,rejected63,
  unknown-age19/stale0, six residuals0, sources~200/50Hz. Telemetry/fullM3 open.
  UDP multisets67864/65672 match. Root1294240robot/0operator is not ARP loss.
- Host322 before live/327 after posthoc guards. SDK72/ROS41 remain prior; no
  rebuild. Eight runtime/two observer hashes fixed and equal controlled fixture,
  provider unchanged. No tests/builds/heavy analysis during live. Raw/source
  provenance, exact public omissions, rules/namespaces/credentials cleanup pass.

Next separately calibrate packet-level queued-versus-dropped ARP observation or
control before mitigation. Historical UNKNOWNs, fullN3/N5, default loaded DDS
discovery, clock/security/resource/hardware and comparison gates remain open.
PR2 draft, Intrinsic/M4 untouched.

### 2026-11-09 — Packet-level ARP queue/drop tracing, no tuning

- Evidence: `evidence/m3-arp-packet-tracing-2026-11-09/README.md`.
  Plan4729f9a, V1 live88ba3f1 FAILED N0/no matches despite30 native replies;
  N5 NOT_EXECUTED. Unsigned namespace/header JMP64 sign extension diagnosed
  after closure. V2 JMP32 fix223d797/kernel BPF regression; V2 live38f0af4
  calibration once each: N0 driver30, N5 known synthetic UDP load drop20/driver10.
  First verifier failure and all original outcomes preserved, no retry.
- New passive raw tracer validates running BTF prototypes/layout/reasons, exact
  owned42-byte reply/netns/ifindex before creation, private skb pointer map keys,
  local monotonic IDs; queue/enqueue/dequeue/driver-start/kfree/consume. Retire
  at driver-start to exclude later bridge/peer frees. CAP_BPF/PERFMON only owned
  endpoints, no privileged/global tracefs/sysctl. Bounded4096IDs/4MiB/1Mevents/600s.
  No pre-queue classifier drop, clone/copy or physical-wire inference.
- Separate loaded plan252ede8/live5544747: default-off --arp-packet-trace with
  loaded ARP/all diagnostics/dynamic/N0-N5/no fault/<=480s guard. Stop load/drain,
  detach tracer before native capture closes. Existing traffic/defaults/provider/
  runtime unchanged. N0/2903/15s8/8PASS. N5/2903/300s121success/122attempts,28skip;
  intent34 REJECTED/context_lost(6/1), not EXPIRED. Matching closed journals,
  receiver dispatched,121effects,0unresolved/UNKNOWN/verified-expired. Original
  harness/capturesPASS/exit0; outer durable and all-success gatesFAIL/exit1.
  Zero active transport context/link events; worker/start-fence cause still open.
- Full N5 tracer operator12driver/0drop; robot26IDs=10driver/16actual QDISC_DROP,
  zero pending/reserve/map/read/collision/otherfree/bulk ambiguity. Source/peer
  native reply counts equal driver counts. Ten robot successful enqueue/dequeue;
  seven69.406–113.944ms,three<1us. Exact inner netem/TBF instruction not located.
- Prospective all32 positive steps inside publication OP11/robot21:18robot
  windows no source reply;13have exactdropIDs,5queued IDs4/13/18/21/22 reachdriver
  1.082–96.874ms after window end. These are new cohort identities, not historic8.
  Four primary>=1sCONTROLgaps remain, none with creation of dropped ARP inside;
  ARP observations do not uniquely explain all gaps or original failures.
- Host336V1/337V2/339loaded/341closed boundaryguards. SDK72/ROS41 prior only;
  eight runtime/two existing observer hashes fixed; new tracer fixed V2→loaded.
  All source verified atclosure and original Git blobs after analysis changes.
  497rawfiles hashed, public omissions explicit;5ownednetworks/containers and
  credentials removed. No tests/builds/heavy analysis whilelive, no tuning.

Next: inspect intent34 worker/start-fence clock/grant context rejection without
replay or tuning; then separately plan mitigation using exact ARP lifetimes.
Original intents98/12 remain UNKNOWN. FullM3/N3/N5/DDSDiscovery/clock/security/
resource/hardware/comparison gates open. PR2 draft, Intrinsic/M4 untouched.

### 2026-11-09 — Command34 start-fence diagnosis, no tuning

- Evidence: `evidence/m3-command34-start-fence-2026-11-09/README.md`; prospective
  plan precedes read-only all122 joins and controlled checks. Original N5 stays
  FAILED121/122,28skips;34 is REJECTED/context_lost6/1 with one SDK handoff,
  matching closed journals/receiver dispatch, not expiry/UNKNOWN/nonexecution.
- Original common clock/hashes verified. Relative source origin: admission eval
  13.700375ms, observed clock deadline27.181747ms, dispatch mutation27.628416ms,
  receiver rejection36.911291ms, sender observation936.653917ms, workload
  observation1104.808125ms. Mutation stamps precede SQLite commit, not fsync or
  handler start. Clock margin13.481372ms; dispatch0.446669ms past observed lease;
  4872.252696ms original mapped budget remains at rejection. Only34 of122 crosses
  last admission clock deadline; next-smallest margin201.803998ms, successful45.
  Later QUERY clock_error2 expired; observation after receiver rejection.
- Source narrows6/1 to post-dispatch coordinator start-check/submission decline
  OR worker consume expired/revoked/invalid OR worker second pre-handler gate.
  ROS backend cannot emit6/1. Point34 covers admission/GET, not execute. Actual
  start grant may refresh after admission and is unlogged. No unique branch,
  actual grant, scheduler/fsync, ARP or session-loss causality claim.
- Separate probe against unchanged execution_pool.cpp passes9 counterfactual
  assertions; old lease rejects at recorded dispatch while refreshed grant can
  start at same time. Never replay/compare supplied historic times to live VM.
  Existing built execution_contract/IPv4/IPv6 start tests once PASS5146/324/324
  assertions, unchanged fixtures. Phase6 clock-lease lapse and phase1 revocation
  both6/1/noeffects; original budget phase4 gives7/3/noeffects. Closed journals
  read immutable. These controlled causes do not reproduce command34 uniquely.
- Host350 PASS (9new guards),3focused existing native tests only; fullSDK72/ROS41
  prior. All14 existing runtime/observer/test binaries unchanged, provider fixed;
  only isolated diagnostic probe built.497original raw hashes reverified,66new
  local artifacts hashed with exact public omissions. No N5 rerun, installed
  build, defaults/policy/clock/rate/queue/neighbor/budget/timeout changes.

Next: bounded default-off post-dispatch start-check/grant/execute/worker-consume
and second-gate observations, calibrated before a new cohort. Original34 cannot
be assigned a unique branch from old fields. Preserve one-use start fences and
journal authority; no tuning yet. Original98/12 UNKNOWN and fullM3 gates open,
PR2 draft/Intrinsic-M4 untouched.

### 2026-11-09 — Targeted start/check/grant/worker tracing, no tuning

- Evidence: `evidence/m3-start-tracing-2026-11-09/README.md`; Plan0527ccf,
  implementationd13d03e, fixture manifest-constructor correction before capture.
  Failed build preparation retained; no case retry. Producers/C++ tests frozen
  for full SDK75-test sequential stop-on-failure run, source/binaries verified
  atclosure. Posthoc reader/harness guards tracked separately with Git blobs.
- Default-off TransportConfig/ROS start_diagnostics requires CommandTrace;
  endpoint matches WorkerOptions flag. Points40submission,41ownercheck/grant,
  42execsubmission,43actualworkerconsume/gate,44coordinatordecline. Correlate
  originalcontext/check/worker token/slot/generation, separate grant/command
  deadlines; explicit unavailable. Two bounded trace lanes/counters unchanged.
- Worker fixed POD observation in64slot sealed memfd, generation release/acquire,
  read after matching IPC reply while record held. Private mappingversion2,
  size/flags/version checks reject mismatches. C++ structures grow: rebuild all
  consumers/workers together. SocketIPCv3/SRT/protobuf/CDR wire unchanged. No
  one-use CAS/revoke/freshness/budget/timeout/default policy change.
- New endpoint cases once each IPv4/IPv6: normal4events+success/effect1;
  coordinatorclockdenial3events40/41error13/44,noexecute,6/1/effects0;
  secondgate4events,consume1thenlategate,nohandler,6/1/effects0; disabled0new
  events/success/effect1.8captures complete,0drops. Synthetic500ms/1.5s leases
  only named fixtures, existing1s probes/3s operationtimeout/5s budget retained.
  Test-only atomic resume API requires explicit preexisting barrier options.
- Existing direct execution-start cases return12 observations acrossfamilies;
  revoked-beforeconsume and clock-lease lapse bothactual3/revoked (owner may
  revoke elapsed grant), so enum3 alone is not session-loss cause. Budget case
 7/3, crashcaseUNKNOWN/noinventedreply, running completion unchanged. No repeat
  race to force2/4 samples; their pool/parser contract guards separate.
- Reader validates bounds/enums/context/generation/availability/gate identity.
  Handles failed execute submission/no token, decline after prior owner grant,
  canceled-owner observation absent explicitly. Harness --start-diagnostics
  requires --command-diagnostics and positive new start records; old ignored
  override cannot produce false enabled report. Disabled scenario omits newparam.
- New isolated SDK75/75, ROS41/41, host364/364 PASS. Builds use separate
  build/install *start-trace-qualified* SDK and *m3-start-trace-ros* ROS prefixes;
  original8runtime+2observers+ARP tracer and previous14binaries fixed. Provider
  untouched.563old+154new raw hashes, exact omissions, closed immutable journal
  selections, removed testcontainers. No heavy work overlaps native captures.

Next: separately freeze a prospective loaded cohort with matched new SDK/ROS
baseline and start tracing; no tuning. Original34 cannot be reclassified, earlier
UNKNOWN98/12 retained. M3/fullmatrix/defaultloadedDDS/clock/security/resources/
hardware/comparison open. PR2 draft, Intrinsic-M4 untouched.

### 2026-11-09 — Prospective matched-build loaded start tracing, no tuning

- Evidence: `evidence/m3-loaded-start-tracing-2026-11-09/README.md`; prospective
  plan before live, frozen sourcea508d0e13ca8384c0e0b0bc97f1fa663c124bcbf.
  Explicit fixed --runtime-layout start-trace requires --skip-build. Validates
  all calibrated SDK/ROS/test binaries/archives and preserved baseline. ROS setup
  prefixes/embedded listener worker path verified; scenario forwards selected
  executable prefix. Default baseline paths unchanged; no runtime build/install
  replacement, provider/dependency/source-policy/traffic/timeouts tuning.
- Once each N0/2903/15s8/8,0skip; N5/2903/300s129/129,21skip. Both strict and
  durable gatesPASS/exit0;8/129closed effects,0expired/UNKNOWN/unresolved/unadmitted,
  zero active context/linkloss. All137 starts fully joined by originalcontext,
  check/worker token/slot/generation to closed journals. Every branch handler
  invoked,consume1/gatepass/returned4/0. No rejection recurrence or missing stage.
- N5 actual minimum consume slack587.290706ms, secondgate587.290415ms; original
  mapped budget atconsume>=4825.898982ms.121grants equal ownerclockdeadline,
  122below original record deadline (not exclusive cause buckets). New intent48
  admission-clock margin386.035498ms but owner has later deadline and actual
  consume slack4827.250313ms. No dispatch past lastadmission deadline. Historical
  34's13.48ms condition not reproduced; never borrow new grant/ID for old intent.
- ARP N5 OP8driver/0drop,robot8driver/9actualQDISC_DROP,0pending/loss/collision/
  unknownfree/bulk ambiguity; native source/peer counts match.23positive steps
  OP7/robot16;11robotmissing-source envelopes=9distinctdropIDs+2latequeued7/17,
  residence59.418/58.471ms, driver11.659/14.076ms afterouterend. Max surviving
  robotresidence96.984ms. One1.203180126s robotCONTROLgap has OP responderreply
  inside/no scoped drop created; no unique causal/historical claim.
- SENSOR75029produced/10582observed,accept-to-receivergap61599/rejected128,
  sixresiduals0,source~200/50Hz; telemetry remainsunqualified. Added observer/new
  binarybaseline prevents mitigation/performance claims or replacing old failures.
- Host374 beforelive; SDK75/ROS41 reused exact prior matched qualification,
  no rebuild/retest. Source/matched/oldbaseline/3observer hashes fixed;717prior
  plus303new raw hashes checked, exact omissions.2ownednetworks/containers and
  credentials removed; roots/features unchanged. No tests/build/heavyanalysis
  overlaps capture. Packet/gap/allattempt joins afterclosed sourceverification.

Next predeclare broader seed coverage on same matched baseline/diagnostics and
observe actual start-lease headroom. No tuning, retry or retroclassification.
Original34 branch unavailable/UNKNOWN98,12 retained; fullM3/N3/N5/DDS/clock/
security/resource/hardware/comparison gates open. PR2 draft/Intrinsic-M4 untouched.

### 2026-11-09 — Predeclared additional start-trace seeds, no tuning

- Evidence: `evidence/m3-start-broader-seeds-2026-11-09/README.md`; frozenlive
  58081d142ae30b52cf4bb07532b68cb3b9f3375b. Added fixed --coverage additional-seeds
  requiring matched start+packet tracing; focused2903default unchanged. Declared
  N0/1701/15s thenN5/1701/300s thenN5/4211/300s, stopfirstfailure/no retries.
- N0 PASS8/8,0skip/effects8. N5/1701 FAIL117success/118attempts,32skip,1unresolved,
  effects117. Original harness/capture gatesPASS/exit0; strict/durable gatesFAIL,
  outerexit1. N5/4211 NOT_EXECUTED asdeclared. No new2903run or fullmatrix claim.
- Originalintent118: source341341538487/deadline346341538487ns, Point5localqueued,
  Point6volatileSubmitResultqueued,29clock_unqualified13 atorigin+16.960125ms,
 21input_dropped/deadline atdeadline+2.624127ms.0originalSDKhandoffs/point25,
 0receiverCOMMAND32 and0start40–44,no receiverjournal. Closed senderUNKNOWN8/
 reconcile_required2/revision0/invalidresult. WorkloadterminalUNKNOWNcounter0 is
 not no uncertainty: driver never got terminal status, rowunresolved.158query
 admission/worker observations,48peererror observations,45NOT_FOUNDstatuspolls;
 stored64/158historywith94omitted explicit. No expiry/nonexecution/replay authority.
- Sourceinputs retains originalproof/origin/deadline onclockunqualified then
 dropspendinginputatdeadline. Generic29doesnotlogexactClockMappererror; its
 clock_error0default isnotqualifiedclockevidence. This0SDKpath differs fromolder
 UNKNOWN98/12withSDK1; old34startbranch remainsunavailable. No causalARP/probe/
 scheduler claim. No active transport context/linkloss observations.
- All117startgroups handlerinvoked/consume1/gatepass/closed4/0,actualminconsume
 slack38.302831ms,gate38.302581ms,commandbudget>=1341.413163ms.118explicitly
 unavailable start, retainedinallattemptanalysis. No recorded worker rejection.
- N5ARP OP7driver/0drop,robot9driver/18actualdrop,0pending/loss/collision/unknown
 free/bulkambiguity; nativecounts match.32positivewindows OP6/robot26;22missing
 robotwindows=18distinctdrops+4latequeuedIDs3/11/17/19. Maxsurvivingrobotresidence
126.729ms. FourCONTROLgaps OP4.200145/1.306023,R1.089744/1.237644s retained.
- SENSOR75053produced/25216observed,gap43926/rejected2760,sixresiduals0;
 telemetry unqualified. Host376new; matchedSDK75/ROS41prior exactbinaries.
 Allsource/matched/oldbaseline/observers/provider fixed, no build/tuning/fault.
1020prior+303new raw hashes checked/exactomissions,2ownednetworks/containers/
 credentials removed,roots/features stable. No heavywork overlaps live.

Next: diagnose source clock qualification and pending-input/journal reconciliation
for118's pre-SDK deadline-drop path; preserve UNKNOWN/one-useproof/no replay.
No forceexpiry or tuning.4211 remainsunexecuted under stoppedplan; newprospective
plan requiredbeforelatercohort. Original34/98/12,fullM3gatesopen,PR2draft,
Intrinsic-M4 untouched.

### 2026-11-09 — Intent118 sender pending-input/journal diagnosis, read-only

- Evidence: `evidence/m3-sender-pending-diagnosis-2026-11-09/README.md` and
  `analysis.json`; reusable `tools/m3_sender_pending_diagnosis.py`. No new live
  run, build, policy change, forced expiry, command replay or journal recovery.
- Clock point29 only logs SessionError13: current source permits ClockError
  unqualified OR expired. Generic clock_error0/deadline0 unused; historical
  interval-width versus probe-age cause cannot be recovered. One point29 means
  once-per-pending notification, not one check or proof of continuous failure.
- Pending input drops 2.624127ms after original deadline. Transport slot release
  has no journal/endpoint completion RPC; queued submit is volatile admission.
  GET/QUERY/NOT_FOUND do not mint tickets or invent a result. Last driver cache
  remains local_queued at371404447417ns; observation ends374237012044ns.
- Newly joined teardown chain for originalsession: trace2 sessionchange at
 374642701836, trace3 invalidate at374642706752, successful trace4 at374653670794.
  This is after observation and28.309508180s after inputdrop. Unchanged sender
  invalidate implementation explains closedUNKNOWN8/reconcile_required2/rev0;
  no per-entry commit trace available. Normal journal destructor merely closes.
  No active-window contextloss claim changes. Audit never opens application
  journal recovery; immutable reads preserve originalfiles.
- 303raw hashes checked before/after, source matches captured manifest, matched
  SDK/ROS and preserved baseline verified twice. Host380 PASS (4new guards).
  Prior exactbinarySDK75/ROS41 qualification reused; no runtime change.

Next: separately calibrated sender-owner clock/defer/release/receipt visibility;
no automatic expiry from diagnostics. UNKNOWN118/98/12 and historical34 retained;
4211 remainsunexecuted, M3/fullmatrix gatesopen, PR2draft/Intrinsic-M4 untouched.

### 2026-11-09 — Default-off sender clock/reconciliation visibility

- Evidence: `evidence/m3-sender-visibility-2026-11-09/README.md`; plan before
  edits/calibration. No loaded run, tuning, forced command expiry or118 replay.
- New sender_diagnostics requires CommandTrace. Point45 captures actual owner
  post-check ClockError, observed bit/probe anchor/signed offset, original
  origin/deadline and optional pre/post clock deadlines at firstdefer/recovery.
  No second check. Point46 distinguishes pending release branches including
  outboundqueued versus drop/flush; no outcome or receipt authority.
- Point47 records sender worker journal replies (operation/error/token), explicit
  entry availability and stored state/reason/revision/context. Point48 records
  caller-event enqueue with localerror/peererror and entry availability. No
  transport-to-coordinator receipt channel or journal mutation is introduced.
  Legacy29 remains unchanged; historical118 exactClockError cannot be recovered.
- Separate `build/m3-sender-visibility`, `install/bridge-sender-visibility`,
  `build/m3-sender-visibility-ros`, `install/m3-sender-visibility-ros`. Explicit
  runtime layout sender-visibility requires skipbuild, verifies both old baseline
  and start-trace baseline; default unchanged. Runner rejects old layout and
  requires positive versioned release/journal/event records when enabled.
- SDK77/77, ROS41/41, host387/387 PASS. Four fresh success controls: IPv4/IPv6,
  enabled/disabled, random IDs/journals, each1effect/1SDKhandoff, original5sbudget.
  Enabled each1release/5journal/3event,0loss; disabled0newrecords. Closed journals
  bothsides4/succeeded/rev3/generation1. Snapshot-only fixtures distinguish
  unobserved/qualified/expired/wide, no command in those fixtures.
- No actual sender clockdefer/recovery occurred in healthycontrols; capture of
  those paths and deadline-drop reconciliation with newbuild still outstanding.
  Larger fixed POD/event and enabled observerwork mean no performance claim.
  Existing synthetic SDK regression failure cases remain separate.
- Both previous runtime inventories/provider fixed;20freshraw and303originalraw
  hashes checked,4complete operatorlogs public, SQLite retainedlocal/hashed and
  immutable entries public. No heavywork overlaps calibration; owned containers
  removed. C++/CMake inputs fixed afterSDKinventory; scenario Pythonlayout extended
  beforeROSbuild, explicitly recorded. No application journal recovery by audit.

Next: new predeclared prospective loaded cohort with this calibrated visibility;
do not silently resume stopped4211. Intent118UNKNOWN, historical34/98/12 retained;
M3/fullmatrix/defaultloadedDDS/clock/security/resources/hardware gatesopen,
PR2draft and Intrinsic/M4 untouched.

### 2026-11-09 — Prospective sender cohort stopped at N0 harness bug

- Evidence: `evidence/m3-sender-loaded-cohort-2026-11-09/README.md`.
  Predeclared N0/1701/15s then N5/1701/300s on calibrated sender-visibility,
  frozen9b221a0563d7317d759caedbabec4be59026056a, host389 before live.
- N0 original harness/outerexit1 FAIL; N5 NOT_EXECUTED under stopfirstfailure.
  No retry, replacement slot or loaded run. Old4211 remains stopped. Original
  `.local/m3/20261109T134421999439Z/run.json` and allraw retain failed verdict.
- Harness bug from9e7557d: unaliased local sender summarize import shadows
  earlier packet summarize throughoutmain, even withsenderflagfalse. Capture
  parsing raises UnboundLocalError. Fixed alias summarize_sender after closed
  source verification; new compiled-scope regressionguard. Host390 PASS afterfix;
  no end-to-end live rerun ofrepair. Runtime/provider unchanged.
- Offline read-only decoding reconciles tcpdump populations and nativev2; original
  failedgate is never promoted. Closedjournals8/8success/effects8/0skip/unresolved,
  all8starts handlerinvoked. Sender45=0,46=8,47=63,48=36,0traceloss. No actual
  senderclockdeferral or loaded telemetry/path diagnosis captured. ARP eachpeer
 1driver/0drop. Onlyfreshintent1–8/newjournals/session/epochs, never118context.
- 148newraw/323priorraw hashes checked, exact public omissions. Fixed new and
  botholdruntime inventories/3observers; oneownednetwork/2containers/credentials/
  rules removed, roots/features unchanged. No heavywork overlapslive. Captured
  source checked beforealiasfix and againstGitblob afterwards. SDK77/ROS41 exact
  binary qualification reused; no rebuild/tuning/forcedexpiry/replay.

Next: a NEW separately frozen cohort after harness repair; do not resume/relabel
the failedplan. Actual loaded senderdeferral stilloutstanding.118UNKNOWN and
historical34/98/12 retained; PR2draft/M3fullgatesopen/Intrinsic-M4 untouched.

### 2026-11-09 — New repaired-harness loaded cohort captures actual sender deferral

- Evidence: `evidence/m3-sender-loaded-repair-cohort-2026-11-09/README.md`.
  New user-authorized plan/frozenb97b86b431e1894facbe87c9398b7bb35525594b,
  exact sender-visibility build, no implementation/runtime change. Priorfailed
  N0 remainsfailed, itsN5notexecuted; this newcohort is separate, onceperslot.
- N0/1701/15s PASS8/8,0skip/effects8. N5/1701/300s PASS128/128,22skip/effects128.
  Both original harness/strict/durable gatespass/exit0, no unresolved/UNKNOWN/
  expired/unadmitted. No retry/tuning/forcedexpiry/historical118replay. Old4211
  remainsunexecuted under stoppedplan. No fullmatrix/mitigation claim.
- New intent3 sender45detail1 ClockError2/expired at68855687781ns; observedprobe
 62373601819ns, age6482085962ns versus5s; excess1482085962ns. Probeoffsetwidth
 6051625ns, drift-expanded19015797ns versus200ms, so recorded cause is probe-age
  expiration atcheck. Prior/postclockdeadlines0/unavailable, never invented.
- Sameintent recovery45detail2 at69240784239ns after385096458ns; newanchor
 69240717739ns, age66500ns, width14348457ns. Originalorigin68844935156/deadline
 73844935156ns unchanged,4604150917ns budget remains.46value4outboundqueued,
 one25SDKhandoff69240809072ns; bothjournals4/0/rev3/validgeneration3.
- Pending journal/event snapshotsstay1/rev0, then2/rev1 and4/rev3.49sender/75all
  originalrequestevents retained. No input/outbounddrop. No actualdeadline-drop
  reconciliation captured. Whyprobeupdatesgap6.482s remainsunproven; notunique
  ARP/qdisc/provider/scheduler cause. Firstdeferonce, notcontinuousclockhistory.
- All136attempts/startgroups joined, handlerinvoked/success;0unavailable/active
  contextloss. N5 minconsume899.657540ms,gate899.657040ms, budget>=1229.803969ms.
  Sendercounts N0:45=0/46=8/47=63/48=36; N5:45=2/46=128/47=3116/48=2002.
- N5 ARP OP6driver/0drop,robot13driver/17actualQDISC_DROP,0pending/loss/other/
  consumed ambiguity.33positive windows,22missing robot envelopes retain17
  distinctdropIDs+5latequeued6/16/23/24/29; maxresidence124.545667ms.3CONTROLgaps:
  OP4.118100169/1.084114958s,robot1.138184376s; no unique clock cause assigned.
  SENSOR75026produced/27663observed,gap43709/rejected391,sixresiduals0;
  telemetry unqualified, source~200/50Hz.
- Host390beforelive, exactSDK77/ROS41qualification reused. Allsource/new/old
  baseline/3observer/provider hashes fixed;303newraw/471priorraw checked, exact
  omissions.2ownednetworks/containers/rules/credentials removed, roots/features
  restored. No tests/builds/heavyanalysis overlapslive. Immutableclosedjournals.
  Numericnew118 hasfreshsession/epochs/origin, old118UNKNOWN retained.

Next: diagnose retained intent3 probe-renewal gap before further instrumentation;
no historical118ClockError retroclassification. Actualdeadline-drop reconciliation
remainsopen; old34/98/12,PR2draft/M3fullgates/Intrinsic-M4 unchanged.

### 2026-11-09 — Intent3 probe-renewal gap, retained evidence only

- Evidence: `evidence/m3-intent3-probe-gap-2026-11-09/README.md`, full derived
  headers/provider/neighbor/root context inanalysis.json, read-only script/guards.
  No newrun/build/tuning/forcedexpiry/replay or application journal recovery.
- Old/new retained anchors62373601819/69240717739ns separate6867115920ns;
  ageatfirstdefer6482085962ns, notsamequantity. Two snapshots notcontinuousprobe
  history. Existing intent3 success/originalbudget/1SDKhandoff unchanged.
- Source1s owner timer attempts begin_probe, schedulesnext evenifbusy; onepending
  probe,2s timeout, matchingecho withage<2s required. SharedCONTROL FIFO/SDK
  backpressure/receive-space gates; no probe-specificattempt/handoff/reject trace.
  probe_busy/not_pending alone do notemit commandtrace. No timer-policy changes.
- PinnedCONTROL forceswireinorder. Reply-length157byteDATA candidate443/msg29
  atoperator65636107154ns cannot havecompleteearlier nativeprefixbefore
 67846142822ns (missing442), wait2210035668ns>2s. ConditionalTimeReply would
  alreadybelate; encryptedpayloadmeansno exactkind/echo/rejection proof.
  Candidate455/msg41 precedesnewanchor1455833ns, prefixavailableatfirsttap;
  compatiblewithrecovery, notauthentication/SDKreadproof. Prefixguards withhold
  missingpredecessors and refusewrap; allcapturedfirstflowpredecessors checked.
- Fixedcontext60373601819..71240717739ns: operator104 owner providerreads,
  maxspacing110.811500ms;robot108/max101.470292ms. No6.8swholeownerstall, but
  shortjitter/backpressureunmeasured. Allstate5/sameidentity,0context/linkloss.
  AllCONTROLdirections active,maxadjacentgap<0.992s; threepriorprimary>=1s
  gapsoccurmuchlater. Retainedanchor-interval deltas OP39/robot256retransmissions,
  OP8NAKsent/robot8received,0undecryptincrement. Contextmax robot17sendbuffer,
  OP9receivebuffer. Aggregateobservations, notperprobe packetreceipt.
- Both108neighborreads REACHABLE/stableMAC,0errors,0scopedARPreplylifetimes.
  Rootwholeinterface OP0/robot2708drop increments,robot6787overlimits; notspecific
  probedrops and no blanketARPabsenceclaim. Reliableordering/recoverydelay fits
  failedclockrenewal despiteUDP/owneractivity; exactprobechain remainsunproven.
- 303raw checked before/after,471otherpriorraw rechecked; allcapturedsource matches, provider52be7c8clean,
  calibrated new/old inventories fixed. Analysis-only packet-order contractguards
  pass; no newruntime qualification claim. Historical118UNKNOWN unchanged.

Next optional diagnostic increment: separately calibrated default-off per-probe
attempt/result/queue/handoff/correlatedecho/admission visibility, preserving1pending
and2s/5sbounds. Do not infer historical118ClockError or forceexpiry. PR2draft,
M3/fullgatesopen,Intrinsic/M4 untouched.

### 2026-11-09 — Calibrated default-off per-probe tracing

- Evidence: `evidence/m3-probe-tracing-2026-11-09/README.md`; planbeforeedits.
  New probe_diagnostics requiresCommandTrace, defaultfalse. No1pending/1sattempt/
 2sreply/5sclockage/budget/rate/queue/expiry decision changes. No new loadedrun,
  forcedliveexpiry orhistorical118replay. Priorbaselines/provider fixed.
- Points50attempt/51queue/52SDK/53admission/54pendingclear. ExistingSessionreceive
  optionalstackoutput exposes validatedt1/t2/t3 andactualmappercall/result; null
  whenoff. No second decode/check, callback, allocation orownerI/O. 53evaluated=t4.
  Managementsequence/session/owner/generation joins51to52, validatedsourceepoch/
  t1/t2/t3 joinscrosspeer. Queue/wire/workerIPC/ROSschemas unchanged; C++objects
  needmatchedrebuild. SDKbracket/bytes actual, acceptance notdelivery.
- Before/after pending disambiguates busy, unmatched andlate replies. Natural
  tickclear54, beginreplacementvisible50; no commandexpiry manufactured. Context
  clear canhaveSID0, keptunavailable ratherthanforcedjoin. FirstEASYNCSND+finalSDK
  recorded, repeatedwouldblock suppressed; boundedlane/dropcounts unchanged.
- Separate SDK/ROS `build/m3-probe-tracing`, `install/bridge-probe-tracing`,
  `build/m3-probe-tracing-ros`, `install/m3-probe-tracing-ros`. Explicitlayout
  probe-tracing requires skipbuild, verifiesallolderbaselinechain. Runner rejects
  oldignoredparameter layouts andrequirespositiveprobe lifecycle perendpoint.
  Sender/start flags compatible, defaultpathsunchanged. No loadedcohort launched.
- SDK79/79,ROS41/41,host396/396 PASS. Fourfreshcommands IPv4/IPv6 enabled/disabled,
  each1effect/1SDKhandoff,matching4/0/rev3/gen1 journals/original5sbudget. Enabled
  each4attempts/8queues/8SDK/8admissions/0clears; actualqualifiedmapper4each,8total
  reciprocalexactechojoins. Disabled0newrecords.8fulltraces,0loss.
- Session-only virtualtime busy/accepted/wrongecho/late/invalidcontext guards
  pass, no commands there. No liveSDKwouldblock/late/clear pathwitnessed; no
  qualificationclaimforthosebranches. BiggerPOD andenabledobserverwork preclude
  timingcomparison/mitigationclaim. Historicalcandidatepacketsnotretrodecoded.
-24newraw/774priorraw checked, immutableclosedjournal selections; rawSQLitelocal
  hashed,8publictraces,exactlognormalization. Allsource/binaryinventories archived.
  Priorbaseline/start/sender installs/provider unchanged. No heavywork overlaps
  SDKcalibration, ownednetwork-nonecontainers removed. PR2draft/M3open/Intrinsic
  untouched. No runtimepolicytuning orold118proofreuse.

Next: separately freeze a prospective loadedprobe-tracing cohort; actualbusy/
late/timeout paths remainuncapturedonnewbuild. Preserve1pending/2s/5s rules,
historical118UNKNOWN andold3/34/98/12 scopes; no forcedexpiry orreplay.

### 2026-11-09 — Delivery acceleration: close instrumentation, target reconciliation

- User requested faster delivery. `DELIVERY_PLAN.md` replaces open-ended forensic
  work with ordered acceptance blockers. Reuse exact builds/checks, preserve old
  uncertainty without reconstructing missing history, publish compact gate
  reports, and measure progress by closed gates. PR2draft/M3open/M4notstarted.
- One final bounded cohort in this probe chain, frozen1fdf7cb9a661284ba295ca377fa3ebf22da99b25:
  `evidence/m3-probe-loaded-cohort-2026-11-09/README.md`. N0/1701/15s8/8,
 0skip/effects8; N5/1701/300s128/128,22skip/effects128. Originalharness/strict/
  durablegates PASS/exit0. No unresolved/UNKNOWN/expired/unadmitted. No retry,
  tuning, forcedexpiry orhistorical118replay; stopped4211 unchanged.
- N5 wholecapture615attempts:443emitted/172busy;443exactprobejoins,398qualified/
 45rejectedoldEchoesagainstnewpendingt1,45naturaltickclears.886SDKsuccess,
 0SDKerrors. Queue-to-SDK max0.950125ms, SDKend-to-peeradmission max3514.765669ms;
  commonVM clock, includesbuffer/order/ownerinterval notuniquenetworkcause.
  MaxacceptedRTT1934.701543ms,minrejected2009.280043ms.427emittedstartinside
  sourcewindow; setup/drainseparate. N0 50qualified/0reject/0busy,30insource.
- Fresh49/85 senderclockdefer/recover, originalsbudgetpreserved/success. No new
  deadline-drop reproduction. Instrumentationloop CLOSED; no automatic newrun or
  tracer toseekunobservedbranches. No broad ARP archaeology repeated.
- Compact gate/493lifecycle/all136commandproofs and2fullN5probeexamples published;
 303newraw/798priorraw hashed/retained, explicitomissions. Allsource/binaries/
  observersfixed,2ownednetworks/containers/rules/credentials removed,roots/features
  restored. Host398prelive, exactSDK79/ROS41reused, no rebuild/heavyworklive.
- NEXT IMPLEMENTATION: bounded opaque authoritative per-admission transport
  receipt, never lossytraceauthority; exactsenderrow conservativeUNKNOWN/
  reconcile_required ondrop, no EXPIRED/success/newticket/unrelatedinvalidation.
  Preserve nonterminalprovisionalUNKNOWN query-first andhigher/finalpeerresults.
  Context/reuse/result-race/restart/storage/capacity gates inDELIVERY_PLAN.md.

After that fix, close remainingN3 ROS SENSOR/DDS/comparison acceptance gates.
Historical118UNKNOWN/34/98/12 remain recorded, not repeated forensic prerequisites.


### 2026-11-09 — Sender receipt correctness gap closed

- `evidence/m3-sender-reconciliation-2026-11-09/README.md`: transport publishes
  queued/SDK-accepted/abandoned on the original opaque one-use sender proof.
  Coordinator retains at most64 receipts and services actual abandonment after
  its original job completes. Not CommandTrace-derived authority. BUSY retains
  the receipt; minting-worker generation/peers/owner/context/payload fence it.
- Exact sender local_queued/rev0 becomes UNKNOWN/reconcile_required only; original
  deadline/result rules preserved. Delayed receipts preserve peer acceptance and
  final success. Unsubmitted refusal now retires its own proof and reconciles its
  row instead of invalidating the session. Real session loss retains its existing
  invalidation behavior. Query-first UNKNOWN stays nonterminal; no new ticket,
  remote cancellation, EXPIRED/success fabrication or unrelated-row mutation.
- Full tracking table now returns BUSY before durable admission. Private worker
  IPC4/op11 rejects older workers and generic forged requests. SDK supervisors,
  consumers and ROS workers require matched rebuild; SRT/ROS schemas unchanged.
- Fresh IPv4/IPv6 real context loss before original5s deadline, exact-row vs
  unrelated preservation, SDK acceptance, unclaimed/forged/foreign/reused/stale
  receipts, paused-worker BUSY/retry, replacement generation, query after reconnect
  without effects, and64+1 capacity pass. Journal tests cover context/payload,
  accepted/final result races, idempotence, owner restart and storage failure.
  Default-off C++ test-only handoff hold has no ROS/CLI/env entry point.
- SDK81/81, ROS41/41, host399/399 PASS. Isolated bridge-sender-reconcile /
  m3-sender-reconcile-ros installations and explicit sender-reconcile --skip-build
  layout verify every preserved baseline in the chain. Old provider clean at
  52be7c86; all1101 priorraw+28 newraw hashes verify,14 closed fresh DBs decoded
  immutable. No builds/heavy tests overlap retained native fixture capture.
- Initial fixture queried disconnected (existing API refuses); reconnect added.
  Storage fixture initially left failure count disabled; armed to0. Initial ROS
  test invocation selected enclosing SDK package; scoped --base-paths ros2 fixes
  invocation, no rebuild. All failed logs retained; no production tuning.

NEXT: actual ROS SENSOR N3 freshness/repair, loaded DDS discovery/comparison and
consolidated acceptance. No new N5/deadline-drop qualification claimed for this
build. Historical118 remains UNKNOWN, old34/98/12/stopped4211 unchanged. No tuning,
forced expiry or historical replay. PR2 draft/M3 open/Intrinsic-M4 untouched.


### 2026-11-09 — Thirty-second N3 matrix audited FAIL; source-slot guard corrected

- Frozen plan/source b5ae42c: baseline/one-loss/two-loss30s for1701,2903,4211,
  once each/stop first failure/no retry. Exact sender-reconcile SDK81/ROS41
  binaries reused. Python-only matched layout/prefix verification and explicit
  cohort selector; generic scenario parser now accepts sender-reconcile prefix.
  Host401 PASS before capture. No rebuild/tests/heavy analysis during live.
- Original harness reports all9 PASS/exit0, but the plan's zero-source-skip gate
  was missing from verify_window. Audit: first5 cases PASS; case6 two-loss2903
  FAIL with3 IMU skipped5ms slots. Average199.910322Hz stays within1%, so the old
  rate-only check passed. Counter5605/trace7006 begins17.451971ms after due;
  publish bracket73.708us, preceding60.125us. Late source invocation established,
  not unique scheduler/DDS/observer causality or transport loss of unsent slots.
- Last3 fresh4211 N3 cases actually executed after missed stop. Retain them as
  supplementary/outside_stop_boundary, not NOT_EXECUTED or qualified continuation.
  Original raw PASS/log unchanged; separate audited planFAIL/firstfailure recorded.
  Earlier progress claim of9 passing cases is corrected by this final audit.
- All9 independently measured transport/fault/freshness subgates pass: rate within
 1%, balances6x0, context/QoS/clock stable, no invalid/receiver rejection beyond
  selected two-source gap, upper age max35.182399ms <250ms, complete source/sample/
  native/PCAP diagnostics. Actual SDK8 one-loss repaired/originaltypedhash while
  classifier installed atall3 starts; SDK7/8 two-loss absent atdrainedcutoff and
  both routes subsequently progress. No lossless/physical-age/comparison claim.
- verify_window now rejects positive/bool/missing skipped_slots evidence or missing
  route even when average rate passes. Host402 PASS after post-capture guard.
  No rerun/cohort replacement, no production source/clock/rate/queue/TTL/provider
  tuning. Frozen111 source hashes verified before guard; original guard Git blob
  matches frozen hash, later guard hash separately retained. Full runtime/archive/
  observer chain fixed, provider unchanged. SDK81/ROS41 reused, notnew executions.
- `evidence/m3-n3-thirty-second-matrix-2026-11-09/`: compact gate report, audited
  execution matrix, exact skip neighbors, fault/capture/accounting/shutdown proof.
 901 newraw files hashed/local,18 closed fresh journals immutable-decoded empty.
 18 owned containers/9 networks/9 credentials removed; controlled children exit0,
  no forced kill. Original historical118/34/98/12/stoppedN5/4211 untouched.

N3 thirty-second matrix remains OPEN/FAIL; no automatic retry or retrospective
zero-skip relaxation. Next ordered work: loaded DDS discovery/comparison with
existing defaults, then consolidated acceptance decisions (including any future
source-slot scheduling allowance). No further tracer/ARP study justified here.
PR2draft/M3open/Intrinsic-M4untouched; no forced expiry/historical replay.


### 2026-11-09 — Current-build default DDS cold confirmation: N0 pass, N5 fail

- Frozen f54f783 two-case plan: system DDS/simultaneous N0/1701/15s then N5/1701/
 60s only after control passes, once each/stop failure/no retry. Python-only matched
  layout/prefix selection for DDS coordinator and simulator, baseline builds fixed.
 407 host checks PASS before live, SDK81/ROS41 reused, no native rebuild/tests or
  heavy analysis during live capture. No new tracer/fragment cut/pacing/default.
- N0 PASS8/8 successful commands/effects,0 skipped offers. Source interval
 15.097493797s, IMU3019/3005 callbacks and joints755/755, actual199.966964/50.008300Hz.
  No stale/invalid/clock-rejected callback; realtime estimated upper histogram
  bins max6/21ms, not SRT conservative clock bounds/physical ages. Max terminal
  observation209.008667ms includes poll wait; original5s/closed matching proof.
- N5 FAIL before measurement,45s sender-readiness wait. Operator46 timeline rows:
  CONTROLpub0/sub1, HELLOpub0/sub1, sent434/received0; sampled maxima also0 reverse
  pubs/callbacks. Robot46rows matches4 endpoints, sent438/received407, notready.
  Both journal/handler/QoS eligible; stable single process epoch each, no failed
  coordinator flag. Both N5 journals empty, no measurement marker/command/effect.
  Robot aborts after operator failure. Nominal60s requested window never executed.
- Whole-run competitor live189 polls,128024.432286bps over48.182803s, actualload
  gate passes;512kbit/16packet/dynamic neighbors/system defaults unchanged. All
  PCAP populations pass/zero kernel drops: N0robot7282/operator7252, N5robot7294/
  operator7312. Different tap totals are not packet-loss subtraction authority.
- Cohort/harness exit1 retained. No retry/control-first fallback/newdecode. Existing
  native4096byte fragmentation mechanism/contradicted ROS N0 transfer hypothesis
  remain separate; no unique original/current fragmentation/ARP/qdisc/CPU cause.
- `evidence/m3-dds-loaded-confirmation-2026-11-09/`: compact gate report, complete
  original verdicts/strict closed command proof, sampled startup states,146 raw
  hashes and4 immutable closed fresh journals. Raw packets/resources/fulltyped/
  source/inspect/environment/journal streams stay local.112 Python source hashes
  and full matched/preserved archive/runtime chain fixed; provider unchanged.
  All6 native children controlled exit0/no forcedkill, both scenarios exit before
  namespace teardown;4 owned containers/2 networks removed; no credential created.

`M3_ACCEPTANCE_REVIEW.md` consolidates the actual remaining gates. DDS cold failure
is a comparison outcome, not an instruction to tune DDS until successful. No
steady-window performance/security/age equivalence follows from a failed startup.
Next: retained N5 SENSOR freshness/bounds assessment and explicit comparison
limitations; no automatic new cohort. N3 auditedFAIL/source-slot decision remains
open and prospective; old historical118/34/98/12/stoppedN5/4211 untouched. PR2draft/
M3open/Intrinsic-M4 untouched; no tuning/forced expiry/replay or acceptance waiver.


### 2026-11-09 — Offline retained N5 SENSOR freshness/bounds assessment

- Explicit user constraint: retained captures only, no tuning/new experiments.
  `tools/m3_n5_sensor_audit.py` reads the whole frozen probe cohort1fdf7cb,
  N0/15s control and N5/1701/300s, never launches peers/traffic or opens journals.
 303 original raw hashes verified before/after; six frozen source Git blobs match
  captured source inventory. Existing probe/sender-reconcile runtime chains fixed.
- N5 source interval300.147813012s,75,037 produced/75,034 ingress/72,240 SDK handoffs/
 28,290 receiver decisions/27,750 publications/typed observations. Histograms are
  full RPC checkpoint deltas, counts22,990IMU/4,760joints; not last diagnostic tail.
  Upper age p50/p95/p99/max bins106/134/144/179ms IMU and113/141/152/183ms joints.
  Exact window maxima178.324341/182.559637ms, each new cumulative maximum, <250ms.
  Six pipeline balances0; empty qualified unchanged-owner/context checkpoints.
- Receiver539 rejected:465 clock age unqualified/invalid,0 stale_sample,74 other
  unclassified. Preserve all47,287 source-unobserved samples;43,950 SDK-to-decoded
  gap is not exclusive WAN loss/FEC retirement. Unknown/missing ages have no
  publication percentile. No per-SAMPLE trace exists in these logs. Ages are
  ingress-to-prepublish authorization under original mapper model, not physical
  sensor age/typed-observer arrival age or uninterrupted availability.
- Frozen fixed8-slot arrays and2 configured sensor routes retain one latest sample
  per route at each persistent ingress/outbound/receive stage. Structural bound,
  not measured high-water. All six pending fields0 at both checkpoints; continuous
  occupancy peak unavailable. Separate BIND/CONTROL/transient/provider/FEC/RMW/
  kernel memory outside this slot claim. No production source or limits changed.
- Complete SENSOR observer:2,983 active sender/2,875 receiver fully source-contained
  reads, one original owner/generation/socket each. Premeasurementrobot-bridge-1
  contributes0 eligible reads and is unavailable, never a0 occupancy peak/stitch.
  Smoothed sender sendbuffer packets0..59,bytes59..26679,flight0..61; receiver
  bytes35..196 despite packet gauge0. No SDKhardpeak claim. FC256/SRT+UDP buffers
 262144 each are checked source requests, not normalized readback/allocator caps.
  Sampled endpoint RSS sums297828352/196771840bytes include observer/workers and
  can double-count/miss peaks; no whole-stack memory/leak/resource-parity proof.
- `evidence/m3-n5-sensor-retained-audit-2026-11-09/`: full assessment/checkpoints,
  input hashes, source/binary proof and compact gate decision.6 new offline guards,
 413 total host checks PASS. Initial focused discovery also counted4 imported
  existing accounting tests; final discovery avoids duplicates. No runtime build/
  experiment/capture/tuning, journal recovery, expiry or historical command replay.

Close the publication-age assessment for this retained run and record structural
bridge bounds; keep continuous availability/queue peaks/hard SDKprocess caps
unavailable. Not newest-build/all-seed/fullN5/M3 acceptance. Next comparison/
acceptance statement with explicit limits and prospective N3 source-slot decision;
no new experiment. N3auditedFAIL, defaultDDSN5coldFAIL and old UNKNOWN/stopped scopes
unchanged. PR2draft/M3open/Intrinsic-M4untouched.


### 2026-11-09 — Comparison and M3 acceptance statement delivered, no experiments

- Explicit user request: comparison/M3 acceptance statement with limits retained,
  no tuning/new experiments. `M3_COMPARISON_AND_ACCEPTANCE.md` is the canonical
  conclusion; `evidence/m3-comparison-acceptance-2026-11-09/` supplies machine
  decision and50-report hash index. Documentation/retained JSON checks only;
  SDK81/ROS41/host413 validation is reused, not re-executed. No runtime/native build,
  capture/traffic, journal open/recovery, forced expiry or historical replay.
- Four original three-seed600s N1/N2 primary totals checked against per-seed rows:
  SRT900/900 successes/effects atN1 andN2,0 skipped offers; DDSN1 892attempts,
 890successes/effects+2receiver-backed expiries,8skips; DDSN2 843attempts,
 830successes/effects+12receiver-backed expiries+1nonadmission,57skips. Distinct
  recorded series, no pooled success probability/current-build/causal ranking.
- Explicit older DDSN2/2903robot population exception170340filtered vs170338file,
  kernel0 remains unreconciled; executionPASS never means all capture/age gates
  qualify. DDSN1/N2 age gate remains open; rejected/unavailable clock populations
  stay out of accepted percentiles with visible denominators. Source ages differ.
- RetainedN5probe build128/128,22skips and all27750 publication upper bounds
  <=182.559637ms support their own command/freshness/slot properties; preserve
 465unknownage/47287source-unobserved and unmeasured queue/memory/availability.
  LatestDDSN0passes8/8; defaultN5coldFAIL before measurement has no steady-window
  denominator, not0% success or a comparative speed/resource ratio.
- No general SRT superiority or DDS equivalence established. Security/cost,
  topology/observer/build/run-time, age origin, tick/RSS/PCAP and hardware limits
  explicit. Demonstrated selective bridge capabilities are distinct from a
  controlled transport advantage. DDS failure is an observed comparator outcome,
  not an instruction to tune until it passes. No unique historical cause assigned.
- Acceptance conclusion: M3 NOT accepted as complete under unchanged plan.
  N3auditedFAIL still5prefixPASS/case6threeIMUskips/last3outside_stop_boundary;
  no threshold relaxation or retry. Latestcandidate lacks complete inherited
  profile/seed proof; older matrices retain exact build scope. Comparison age/
  capture/nonmeasurement boundaries remain explicit. No invented mandatory hard
  memory/hardware threshold, waiver, merge or M4 authorization.

The comparison/acceptance reporting request is complete; open qualification is
not hidden and no new experiment is queued automatically. M0–M2 retain recorded
acceptance; PR2draft/M3open/Intrinsic-M4untouched. Future scope/source-slot changes
must be explicit/prospective and cannot retrospectively reclassify failed cases.


### 2026-11-09 — Concrete N3/current-build closure plan, no execution

- User requests concrete remaining-M3 plan starting N3/current-build coverage,
  without tuning/new experiments. `M3_CLOSURE_PLAN.md` and
  `evidence/m3-closure-plan-2026-11-09/{plan,coverage-ledger,readiness}.json`
  are prepared planning artifacts, execution disabled/not scheduled. No runtime
  build/test/traffic/capture/journal recovery/expiry/replay or threshold change.
- Fixed planning candidate sender-reconcile-929d1f7c7727; full manifest SHA
 929d1f7c7727b6c9ba363762074557873d0ffeb6ed6a2b4ab75957d341ee0fc7.
  Read-only matched/preserved-chain check:13 binary/archive/test entries match,
 86 recorded native inputs unchanged, provider clean at52be7c86. SDK81/ROS41/
  host413 retained, not rerun. Future harness changes need a fresh driver freeze;
  no production native rebuild required merely to select the existing candidate.
- Applied current zero-skip window guard to9 hash-checked original N3 result
  JSONs, offline only. First5 remain qualifying prefix; case6threeIMUskips is
  rejected; last3 individual window checks pass but remain outside_stop_boundary.
  No cohort splice/resumption/retroactive9of9PASS, no relaxed gate. Future strict
  route, if explicitly authorized, is one new9-case30s baseline/one/two-loss
  cohort at1701,2903,4211; stop first failed gate, no retry-until-pass.
- Concrete current-build readiness blockers: tools/m3_n4.py still binds oldSDK/
  peer executable; tools/m3_n4_ros.py binds oldROS. Need isolated currentIPC4 peer
  link and explicit SDK/worker/ROS child prefix checks before N4 current-build
  claims. All-stage strict orchestrator also not ready; raw run_m3 exit0 must not
  schedule later slots before independent progress/source/capture/cleanup checks.
  No adapter/assessor implementation or fixture build performed in this task.
- Proposed future order/counts, not authorization: N3x9, combinedN0/300sx1,
  N4x19 (4native phasesx3directions+QUERYx1+ROSsensorx3+ROScrashx3),
  N1x3/600s,N2x3/600s,N5x3/300s.38 cases total; N3+combined nominal source5070s/
 84.5min excludes N4/all overhead, not wallclock promise. N4 sensor adds45 nominal
  source seconds. No six-second expiry experiment, no newDDS candidate/cold run.
- Gates and outputs fixed: N3 zero skips/1%/30..31s, original trace budgets and
  selected SDK source/parity identities; combined full populations/age<=250ms/
  sixbalances/positive strict closed-success progress; phase-specific N4 safe
  outcomes remain separate from all-success progress. First failed declared gate,
  hash drift, timeout or cleanup failure stops all later work; actually executed
  after missed gate remains explicit. No tuning/retry/fallback/old4211resume.

The concrete planning request is complete; no new experiment follows automatically.
Further prep can remain offline, but current no-new-experiments scope must be
explicitly changed before live execution. Current M3notaccepted/PR2draft/M4untouched
and comparison limits remain. This plan creates no waiver or merge permission.


### 2026-11-09 — Offline closure source preparation

- Current continue scope remains no tuning/new experiments. No builds, Docker,
  ROS/fixture launches, traffic/capture, journal recovery, forced expiry or replay.
- N4 native/ROS runners now select explicit layouts, verify child prefixes and
  preserve all production timing/settings. Standalone CMake imports the selected
  SDK worker and emits peer/SDK/header/archive/provider/source binding metadata.
  Private IPC4 retains existing CLI flag `--worker-ipc-v3`. Nonbaseline missing or
  stale binding refuses before output/lab creation. Actual candidate fixture is
  not built; binding remains absent. CMake source-reviewed only.
- New closed-case strict assessor reuses N3 raw validators, combined SENSOR and
  durable command progress, N4 phase/freshness/crash outcomes, frozen provenance,
  outage kernel/bracket/drop checks and recorded cleanup. Combined capture uses
  original summaries rather than independent full packet reparsing. Callback-only
  stop controller is offline-tested; no live dispatcher is implemented/wired.
-427 offline Python checks pass. Read-only retained N3 baseline passes, known
  two-loss2903 still rejects skipped slots. All13 candidate manifest entries and
 86 native inputs unchanged, provider52be7c86 clean/archive unchanged. No SDK/ROS
  rebuild/tests repeated; prior SDK81/ROS41 retain their original scope.
- Evidence: `evidence/m3-offline-closure-preparation-2026-11-09/README.md`,
  readiness-update/verification/source-snapshot JSON and validation logs. Snapshot
  has null native fixture binding and is not a complete live campaign freeze.
- Next offline work: live-dispatcher design/wiring with prospective freeze and
  mocked transitions. Isolated fixture build/link and any live qualification
  remain pending separately authorized scope. All38 planned cases disabled;
  M3notaccepted/PR2draft/M4untouched. Do not retry/splice old N3 or replay118.
