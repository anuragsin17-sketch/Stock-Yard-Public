// Position Tracking UI Component
// Add this script to index.html to enable position tracking in Radar tab

function displayPerformanceTracking() {
    const container = document.getElementById('resultsContainer');
    
    if (!screeningData) {
        container.innerHTML = '<div class="mobile-card rounded-xl p-5 text-center text-slate-400">Loading...</div>';
        return;
    }
    
    // Load positions data
    fetch('positions.json')
        .then(response => response.json())
        .then(positionsData => {
            displayPositionsUI(positionsData, container);
        })
        .catch(error => {
            console.log('No positions data available yet:', error);
            displayPositionsUI({open_positions: [], closed_positions: []}, container);
        });
}

function displayPositionsUI(positionsData, container) {
    const openPositions = positionsData.open_positions || [];
    const closedPositions = positionsData.closed_positions || [];
    
    // Calculate statistics
    const totalOpen = openPositions.length;
    const totalClosed = closedPositions.length;
    const avgGain = closedPositions.length > 0 
        ? (closedPositions.reduce((sum, pos) => sum + pos.gain_percent, 0) / closedPositions.length).toFixed(2)
        : 0;
    const totalUnrealized = openPositions.reduce((sum, pos) => sum + (pos.current_gain_percent || 0), 0).toFixed(2);
    
    let html = `
        <div class="mobile-card rounded-xl p-5 mb-5">
            <h3 class="text-lg font-bold text-slate-100 mb-4 tracking-tight">Position Tracking</h3>
            <div class="grid grid-cols-2 gap-5 mb-5">
                <div class="text-center">
                    <div class="text-3xl font-bold mono" style="color: #D97706;">${totalOpen}</div>
                    <div class="text-xs text-slate-400 tracking-wider uppercase mt-1">Open Positions</div>
                </div>
                <div class="text-center">
                    <div class="text-3xl font-bold mono" style="color: #047857;">${totalClosed}</div>
                    <div class="text-xs text-slate-400 tracking-wider uppercase mt-1">Closed Positions</div>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-5">
                <div class="text-center">
                    <div class="text-xl font-bold mono" style="color: #3B82F6;">${totalUnrealized}%</div>
                    <div class="text-xs text-slate-400 tracking-wider uppercase mt-1">Unrealized Gain</div>
                </div>
                <div class="text-center">
                    <div class="text-xl font-bold mono" style="color: #10B981;">${avgGain}%</div>
                    <div class="text-xs text-slate-400 tracking-wider uppercase mt-1">Avg Closed Gain</div>
                </div>
            </div>
        </div>
        
        <!-- Filter Buttons -->
        <div class="mobile-card p-3 mb-5">
            <div class="flex space-x-3">
                <button id="filterOpen" class="pill-tab flex-1 text-xs font-medium transition-all touch-btn active">
                    Open (${totalOpen})
                </button>
                <button id="filterClosed" class="pill-tab flex-1 text-xs font-medium transition-all touch-btn text-slate-400">
                    Closed (${totalClosed})
                </button>
            </div>
        </div>
        
        <!-- Open Positions Container -->
        <div id="openPositionsContainer">
    `;
    
    if (openPositions.length > 0) {
        openPositions.forEach(pos => {
            const chartUrl = `https://in.tradingview.com/chart/?symbol=NSE:${pos.symbol}`;
            const gainColor = pos.current_gain_percent >= 0 ? '#10B981' : '#EF4444';
            const targetProgress = (pos.current_gain_percent / 20 * 100).toFixed(0);
            
            html += `
                <div class="mobile-card rounded-xl p-5 mb-4">
                    <div class="flex justify-between items-start mb-3">
                        <div class="flex-1">
                            <a href="${chartUrl}" target="_blank" class="text-lg font-bold text-slate-100 hover:text-blue-400 transition-colors">${pos.symbol}</a>
                            <div class="text-xs text-slate-400 mt-1">${pos.company_name}</div>
                            <div class="text-xs text-slate-500 mt-1">${pos.category}</div>
                        </div>
                        <span class="px-3 py-1.5 text-xs rounded-full mono tracking-wide" style="background: rgba(217, 119, 6, 0.2); color: #D97706;">OPEN</span>
                    </div>
                    
                    <div class="grid grid-cols-2 gap-3 mb-3">
                        <div>
                            <div class="text-xs text-slate-500">Entry Price</div>
                            <div class="text-sm font-bold mono text-slate-100">₹${pos.entry_price.toLocaleString()}</div>
                        </div>
                        <div>
                            <div class="text-xs text-slate-500">Current Price</div>
                            <div class="text-sm font-bold mono text-slate-100">₹${pos.current_price.toLocaleString()}</div>
                        </div>
                        <div>
                            <div class="text-xs text-slate-500">Target (20%)</div>
                            <div class="text-sm font-bold mono" style="color: #047857;">₹${pos.target_price.toLocaleString()}</div>
                        </div>
                        <div>
                            <div class="text-xs text-slate-500">Current Gain</div>
                            <div class="text-sm font-bold mono" style="color: ${gainColor};">${pos.current_gain_percent >= 0 ? '+' : ''}${pos.current_gain_percent}%</div>
                        </div>
                    </div>
                    
                    <!-- Progress Bar -->
                    <div class="mb-2">
                        <div class="flex justify-between text-xs text-slate-500 mb-1">
                            <span>Progress to Target</span>
                            <span>${targetProgress}%</span>
                        </div>
                        <div class="w-full bg-slate-700 rounded-full h-2">
                            <div class="h-2 rounded-full transition-all" style="width: ${Math.min(targetProgress, 100)}%; background: linear-gradient(90deg, #D97706, #047857);"></div>
                        </div>
                    </div>
                    
                    <div class="text-xs text-slate-500 mt-2">
                        Entry: ${new Date(pos.entry_date).toLocaleDateString('en-IN')}
                    </div>
                </div>
            `;
        });
    } else {
        html += `
            <div class="mobile-card rounded-xl p-6 text-center">
                <div class="text-slate-400 mb-2">No Open Positions</div>
                <div class="text-xs text-slate-500">Positions will appear when stocks hit trigger prices</div>
            </div>
        `;
    }
    
    html += `</div>`;
    
    // Closed Positions Container (hidden by default)
    html += `<div id="closedPositionsContainer" class="hidden">`;
    
    if (closedPositions.length > 0) {
        closedPositions.forEach(pos => {
            const chartUrl = `https://in.tradingview.com/chart/?symbol=NSE:${pos.symbol}`;
            const gainColor = pos.gain_percent >= 0 ? '#10B981' : '#EF4444';
            
            html += `
                <div class="mobile-card rounded-xl p-5 mb-4" style="border-color: rgba(16, 185, 129, 0.3);">
                    <div class="flex justify-between items-start mb-3">
                        <div class="flex-1">
                            <a href="${chartUrl}" target="_blank" class="text-lg font-bold text-slate-100 hover:text-blue-400 transition-colors">${pos.symbol}</a>
                            <div class="text-xs text-slate-400 mt-1">${pos.company_name}</div>
                            <div class="text-xs text-slate-500 mt-1">${pos.category}</div>
                        </div>
                        <span class="px-3 py-1.5 text-xs rounded-full mono tracking-wide" style="background: rgba(16, 185, 129, 0.2); color: #10B981;">CLOSED</span>
                    </div>
                    
                    <div class="grid grid-cols-3 gap-3 mb-3">
                        <div>
                            <div class="text-xs text-slate-500">Entry</div>
                            <div class="text-sm font-bold mono text-slate-100">₹${pos.entry_price.toLocaleString()}</div>
                        </div>
                        <div>
                            <div class="text-xs text-slate-500">Exit</div>
                            <div class="text-sm font-bold mono text-slate-100">₹${pos.exit_price.toLocaleString()}</div>
                        </div>
                        <div>
                            <div class="text-xs text-slate-500">Gain</div>
                            <div class="text-sm font-bold mono" style="color: ${gainColor};">${pos.gain_percent >= 0 ? '+' : ''}${pos.gain_percent}%</div>
                        </div>
                    </div>
                    
                    <div class="flex justify-between text-xs text-slate-500">
                        <span>Entry: ${new Date(pos.entry_date).toLocaleDateString('en-IN')}</span>
                        <span>Exit: ${new Date(pos.exit_date).toLocaleDateString('en-IN')}</span>
                    </div>
                </div>
            `;
        });
    } else {
        html += `
            <div class="mobile-card rounded-xl p-6 text-center">
                <div class="text-slate-400 mb-2">No Closed Positions</div>
                <div class="text-xs text-slate-500">Closed positions will appear when targets are hit</div>
            </div>
        `;
    }
    
    html += `</div>`;
    
    // Info section
    html += `
        <div class="mobile-card rounded-xl p-5 mt-5" style="border-color: rgba(4, 120, 87, 0.2); background: rgba(4, 120, 87, 0.1);">
            <h4 class="text-sm font-bold mb-3 tracking-wider uppercase" style="color: #047857;">How Position Tracking Works</h4>
            <div class="text-xs text-slate-300 space-y-2">
                <div>• <strong>Position Taken:</strong> Automatically triggered when stock price reaches trigger price (within 1%)</div>
                <div>• <strong>Target:</strong> 20% gain from entry price</div>
                <div>• <strong>Position Closed:</strong> Automatically closed when target is hit</div>
                <div>• <strong>Updates:</strong> Positions are checked 4 times daily via GitHub Actions</div>
                <div>• <strong>No Manual Action:</strong> Everything runs automatically 24/7</div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Add filter button event listeners
    document.getElementById('filterOpen').addEventListener('click', () => {
        document.getElementById('filterOpen').classList.add('active');
        document.getElementById('filterOpen').classList.remove('text-slate-400');
        document.getElementById('filterClosed').classList.remove('active');
        document.getElementById('filterClosed').classList.add('text-slate-400');
        document.getElementById('openPositionsContainer').classList.remove('hidden');
        document.getElementById('closedPositionsContainer').classList.add('hidden');
    });
    
    document.getElementById('filterClosed').addEventListener('click', () => {
        document.getElementById('filterClosed').classList.add('active');
        document.getElementById('filterClosed').classList.remove('text-slate-400');
        document.getElementById('filterOpen').classList.remove('active');
        document.getElementById('filterOpen').classList.add('text-slate-400');
        document.getElementById('closedPositionsContainer').classList.remove('hidden');
        document.getElementById('openPositionsContainer').classList.add('hidden');
    });
}
