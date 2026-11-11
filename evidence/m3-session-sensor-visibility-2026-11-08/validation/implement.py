from pathlib import Path
p=Path('src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/provider_diagnostics.hpp');s=p.read_text().replace('unsigned state_before=0','unsigned channel=0; // 0 CONTROL, 1 SENSOR; streams have independent budgets.\n    unsigned state_before=0').replace('double rtt_ms=0;', '''double rtt_ms=0;
    // Pinned srt_bstats totals; aggregate drops are not reason-specific events.
    std::int64_t unique_sent=0,unique_received=0,sender_loss=0,receiver_loss=0,sender_drop=0,receiver_drop=0;
    std::int64_t sender_filter_extra=0,receiver_filter_extra=0,receiver_filter_supply=0,receiver_filter_loss=0;
    int flow_window_packets=0,congestion_window_packets=0;
'''.rstrip());p.write_text(s)
p=Path('src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/transport.hpp');s=p.read_text().replace('std::shared_ptr<SampleTrace> sample_trace{};', 'std::shared_ptr<ProviderDiagnostics> sensor_provider_diagnostics{}; // Independent opt-in SENSOR SDK reads.\n    std::shared_ptr<SampleTrace> sample_trace{};');p.write_text(s)
p=Path('src/robotweax_srt_bridge_core/src/transport/transport.cpp');s=p.read_text().replace('next_probe=0,next_provider_sample=0;', 'next_probe=0;std::array<std::uint64_t,2> next_provider_sample{};')
a=s.index('    void provider_sample(');b=s.index('    void drop(',a);block=s[a:b]
block=block.replace('provider_sample(bool before_close=false)','provider_sample(unsigned i,bool before_close=false)').replace('if(!config.provider_diagnostics||config.provider_diagnostics->exhausted())return;', 'auto& diagnostics=i?config.sensor_provider_diagnostics:config.provider_diagnostics;\n        if(!diagnostics||diagnostics->exhausted())return;').replace('next_provider_sample','next_provider_sample[i]').replace('ProviderObservation o;o.begin_ns=now;', 'ProviderObservation o;o.channel=i;o.begin_ns=now;').replace('links[0]','links[i]').replace('o.flight_packets=stats.pktFlightSize;o.rtt_ms=stats.msRTT;', '''o.flight_packets=stats.pktFlightSize;o.rtt_ms=stats.msRTT;
                    o.unique_sent=stats.pktSentUniqueTotal;o.unique_received=stats.pktRecvUniqueTotal;
                    o.sender_loss=stats.pktSndLossTotal;o.receiver_loss=stats.pktRcvLossTotal;
                    o.sender_drop=stats.pktSndDropTotal;o.receiver_drop=stats.pktRcvDropTotal;
                    o.sender_filter_extra=stats.pktSndFilterExtraTotal;o.receiver_filter_extra=stats.pktRcvFilterExtraTotal;
                    o.receiver_filter_supply=stats.pktRcvFilterSupplyTotal;o.receiver_filter_loss=stats.pktRcvFilterLossTotal;
                    o.flow_window_packets=stats.pktFlowWindow;o.congestion_window_packets=stats.pktCongestionWindow;''').replace('config.provider_diagnostics->record(o)', 'diagnostics->record(o)')
s=s[:a]+block+s[b:];s=s.replace('if(i==0&&links[0].fd!=SRT_INVALID_SOCK)provider_sample(true);','if(links[i].fd!=SRT_INVALID_SOCK)provider_sample(i,true);').replace('timers();provider_sample();','timers();provider_sample(0);provider_sample(1);');p.write_text(s)
p=Path('ros2/robotweax_srt_bridge/src/bridge_node.cpp');s=p.read_text().replace('std::shared_ptr<core::ProviderDiagnostics> provider_diagnostics_;','std::shared_ptr<core::ProviderDiagnostics> provider_diagnostics_,sensor_provider_diagnostics_;')
s=s.replace('void provider_diagnostics(){\n        if(!provider_diagnostics_)return;', 'void provider_diagnostics_stream(const std::shared_ptr<core::ProviderDiagnostics>& diagnostics,bool sensor){\n        if(!diagnostics)return;').replace('provider_diagnostics_->poll(o)', 'diagnostics->poll(o)').replace('line<<"PROVIDER_STATS {";', 'line<<(sensor?"SENSOR_PROVIDER_STATS {":"PROVIDER_STATS {");')
needle='            line<<",\\\"owner_epoch\\\":\\\""<<hex(o.owner_epoch)'
a=s.index(needle)
s=s[:a]+'''            if(sensor){
                line<<",\\\"schema_version\\\":1,\\\"channel\\\":"<<o.channel;
'''+''.join('                line<<",\\\"'+k+'\\\":"<<o.'+k+';\n' for k in ['unique_sent','unique_received','sender_loss','receiver_loss','sender_drop','receiver_drop','sender_filter_extra','receiver_filter_extra','receiver_filter_supply','receiver_filter_loss','flow_window_packets','congestion_window_packets'])+'''            }
'''+s[a:]
a=s.index('    void provider_diagnostics_stream(');b=s.index('\n    }',a)+len('\n    }');s=s[:b]+'''
    void provider_diagnostics(){
        provider_diagnostics_stream(provider_diagnostics_,false);
        provider_diagnostics_stream(sensor_provider_diagnostics_,true);
    }
'''+s[b:]
needle='        if(declare_parameter<bool>("sample_diagnostics",false))';s=s.replace(needle,'        if(declare_parameter<bool>("sensor_provider_diagnostics",false)){sensor_provider_diagnostics_=std::make_shared<core::ProviderDiagnostics>();transport.sensor_provider_diagnostics=sensor_provider_diagnostics_;}\n'+needle)
needle='            if(command_trace_)std::cout<<"COMMAND_TRACE_STATUS'
a=s.index(needle);s=s[:a]+'''            if(sensor_provider_diagnostics_)std::cout<<"SENSOR_PROVIDER_STATS_STATUS {\\\"schema_version\\\":1,\\\"channel\\\":1,\\\"attempted\\\":"<<sensor_provider_diagnostics_->attempted()<<",\\\"dropped\\\":"<<sensor_provider_diagnostics_->dropped()<<",\\\"exhausted\\\":"<<sensor_provider_diagnostics_->exhausted()<<",\\\"limit\\\":"<<sensor_provider_diagnostics_->limit()<<"}"<<std::endl;
'''+s[a:];p.write_text(s)
p=Path('ros2/robotweax_srt_bridge_demo/scripts/m3_scenario.py');s=p.read_text().replace("'sample_diagnostics':", "'sensor_provider_diagnostics': str(getattr(self.args,'sensor_provider_diagnostics',False)).lower(),\n            'sample_diagnostics':").replace("    parser.add_argument('--provider-diagnostics',action='store_true')", "    parser.add_argument('--provider-diagnostics',action='store_true')\n    parser.add_argument('--sensor-provider-diagnostics',action='store_true')");p.write_text(s)
p=Path('tools/run_m3.py');s=p.read_text().replace("    parser.add_argument('--provider-diagnostics'", "    parser.add_argument('--sensor-provider-diagnostics',action='store_true',help='separate bounded SENSOR SDK statistics; adds observer work')\n    parser.add_argument('--provider-diagnostics'")
s=s.replace("report['provider_diagnostics_enabled']=args.provider_diagnostics", "report['provider_diagnostics_enabled']=args.provider_diagnostics\n    report['sensor_provider_diagnostics_enabled']=args.sensor_provider_diagnostics").replace("(['--provider-diagnostics'] if args.provider_diagnostics else [])", "(['--provider-diagnostics'] if args.provider_diagnostics else [])+(['--sensor-provider-diagnostics'] if args.sensor_provider_diagnostics else [])")
s=s.replace("        if args.provider_diagnostics:\n", "        if args.sensor_provider_diagnostics:\n            try:report['sensor_provider_diagnostics']=m3_provider_stats.summarize_run(run,sensor=True)\n            except Exception as error:report['status']='failed';report['sensor_provider_diagnostics_error']=str(error)\n        if args.provider_diagnostics:\n")
p.write_text(s)
