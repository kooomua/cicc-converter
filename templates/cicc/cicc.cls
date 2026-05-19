\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{cicc}[2024/05/06 Communications in Computational Chemistry Class]

% ==============================================================================
% 1. 核心定义与声明 (Core Identification)
% ==============================================================================
\LoadClass[twocolumn,twoside]{article}

% ==============================================================================
% 2. 基础页面几何设定 (Layout & Geometry)
% ==============================================================================
% 使用 includehead 确保页眉高度被计算在边距内，防止与正文冲突
\RequirePackage[
  a4paper,
  left=0.6in,
  right=0.6in,
  top=0.2in,
  bottom=0.2in,
  headheight=45pt, % 增加高度以容纳首字母缩写和期刊信息
  headsep=5pt,
  footskip=0.4in,
  includehead,
  includefoot
]{geometry}

% ==============================================================================
% 3. 字体与编码 (Fonts & encoding)
% ==============================================================================
\RequirePackage[T1]{fontenc}
\RequirePackage[utf8]{inputenc}
\RequirePackage{newtxtext, newtxmath} % 泰晤士风格字体
\RequirePackage{microtype}           % 改善间距调整

% ==============================================================================
% 4. 必需宏包加载 (Required Packages)
% ==============================================================================
\RequirePackage{graphicx}
\RequirePackage{xcolor}
\RequirePackage{etoolbox}
\RequirePackage{amsmath}
\RequirePackage{calc}
\RequirePackage{xstring}
\RequirePackage{authblk}  % 作者机构处理
\RequirePackage{cuted}    % 双栏中的单栏环境 (strip)
\RequirePackage{lipsum}   % 占位文本

% ==============================================================================
% 5. 期刊元数据定义 (Journal Metadata)
% ==============================================================================
\newcommand{\journalfullname}[1]{\gdef\@journalfullname{#1}}
\newcommand{\journalabbrevname}[1]{\gdef\@journalabbrevname{#1}}
\newcommand{\volume}[1]{\gdef\@volume{#1}}
\newcommand{\issue}[1]{\gdef\@issue{#1}}
\newcommand{\doi}[1]{\gdef\@doi{#1}}
\newcommand{\articletype}[1]{\gdef\@articletype{#1}}

% --- 修改日期元数据的初始状态 ---
\newcommand{\receiveddate}[1]{\gdef\@receiveddate{#1}}
\newcommand{\revisiondate}[1]{\gdef\@revisiondate{#1}}
\newcommand{\accepteddate}[1]{\gdef\@accepteddate{#1}}
\newcommand{\onlinedate}[1]{\gdef\@onlinedate{#1}}
\newcommand{\publisheddate}[1]{\gdef\@publisheddate{#1}}
\newcommand{\publishedyear}[1]{\gdef\@publishedyear{#1}}

% 将默认值设为空
\gdef\@receiveddate{}
\gdef\@revisiondate{}
\gdef\@accepteddate{}
\gdef\@onlinedate{}
\gdef\@publisheddate{}
\gdef\@publishedyear{}

% --- 核心逻辑替换：简洁的起始页设置 ---
\RequirePackage{totpages}
\RequirePackage{refcount}
\newcommand{\firstpage}[1]{%
  \setcounter{page}{#1}% 直接设置页码
  \gdef\@pagenumbers{%
    % \the\value{page}--\the\numexpr#1 + \getrefnumber{TotPages} - 1\relax%
    #1--\the\numexpr#1 + \getrefnumber{TotPages} - 1\relax%      
  }%
}


% 默认值设定
\journalfullname{Communications in Computational Chemistry}
\journalabbrevname{Commun. Comput. Chem.}
\articletype{Communications}
\doi{doi: 10.4208/cicc.2026.xxx}
\volume{xx}
\issue{xx}
\publishedyear{xxxx}
\receiveddate{dd/mm/yyyy}
\revisiondate{dd/mm/yyyy} 
\accepteddate{dd/mm/yyyy}
\onlinedate{dd/mm/yyyy}
\publisheddate{dd/mm/yyyy}
% \firstpage{x}
%\pagenumbers{1-10}

% ==============================================================================
% 6. 标题与作者逻辑 (Title & Author Logic)
% ==============================================================================
% 短标题逻辑
\newcommand{\shorttitle}{}
\renewcommand{\title}[2][]{%
  \gdef\@title{#2}
  \if\relax\detokenize{#1}\relax \gdef\shorttitle{#2} \else \gdef\shorttitle{#1} \fi
}

% 自动获取第一作者用于页眉
\newcounter{authorcount}
\newcommand{\firstauthorname}{}
\NewCommandCopy\origauthor\author
\renewcommand{\author}[2][]{%
  \stepcounter{authorcount}%
  \ifnum\value{authorcount}=1 \gdef\firstauthorname{#2} \fi
  \ifx&#1& \origauthor{#2} \else \origauthor[#1]{#2} \fi
}
\newcommand{\authorheader}{%
  \ifnum\value{authorcount}>1 \firstauthorname\ et al. \else \firstauthorname \fi
}

% ==============================================================================
% 7. 标题区定制 (Maketitle Redefinition)
% ==============================================================================
\renewcommand\Affilfont{\small\raggedright}
\def\@maketitle{%
  \newpage \null
  \vspace{-2em}
  \begin{flushleft}
    \let \footnote \thanks
    {\LARGE\bfseries \@title \par}
    \vspace{1.5em}
    {\large \@author \par}
    \vspace{1em}
% --- 重新定义的日期显示逻辑 ---
    {\footnotesize 
      % 检查 Received Date
      \ifcsvoid{@receiveddate}{}{Received: \@receiveddate}%
      % 检查 Revision Date，如果有值，前面加个分号隔开
      \ifcsvoid{@revisiondate}{}{; Revision: \@revisiondate}%
      % 检查 Accepted Date
      \ifcsvoid{@accepteddate}{}{; Accepted: \@accepteddate}%
      % 检查 Online Date
      \ifcsvoid{@onlinedate}{}{; Online: \@onlinedate}%
      % 检查 Online Date
      \ifcsvoid{@publisheddate}{}{; Published: \@publisheddate}%          
      . % 句尾点号
    }    
% {\footnotesize 
% Received: \@receiveddate; Revision: \@revisiondate; 
% Accepted: \@accepteddate; Online: \@onlinedate.}
  \end{flushleft}
  \par
}

% ==============================================================================
% 8. 摘要、关键词与图文摘要 (Abstract & GA)
% ==============================================================================
\RequirePackage[runin]{abstract}
\setlength{\abstitleskip}{-1em}
\setlength{\absparindent}{0em}
\setlength{\absleftindent}{1em}
\setlength{\absrightindent}{1em}
\abslabeldelim{:}

\newcommand{\keywords}[1]{%
  \par\vspace{0.5em}
  \noindent{\small\textbf{Key words:}} #1
}

% 装饰线逻辑
\BeforeBeginEnvironment{abstract}{\par\centering\rule{\textwidth - 2em}{0.5pt}}
\AfterEndEnvironment{abstract}{\par\centering\rule{\textwidth - 2em}{0.5pt}\vspace{1em}}

% 图文摘要 (Graphical Abstract)
\newcommand{\graphicalabstractname}{Graphical Abstract}
\newenvironment{graphicalabstract}{%
  \vspace{1em} \noindent
  \begin{minipage}{\textwidth - 2em}
    \begin{flushleft}
      \noindent\textbf{\small\graphicalabstractname:} \par\vspace{0.8em}
    }{%
      \par\vspace{1.5em}
      \noindent\rule{\textwidth}{0.5pt}
    \end{flushleft}
  \end{minipage} \vspace{1.5em}
}

% ==============================================================================
% 9. 页眉页脚设定 (Header & Footer)
% ==============================================================================
\RequirePackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{1pt}

% 奇数页页眉：显示标题
% \fancyhead[LO]{\textit{\shorttitle}}
\fancyhead[LO]{\textit{\small \authorheader / \@journalabbrevname, \@publishedyear, \@volume(\@issue), \@pagenumbers}}
\fancyfoot[CO]{\thepage}

% 偶数页页眉：显示作者和期刊信息
\fancyhead[RE]{\textit{\small \authorheader / \@journalabbrevname, \@publishedyear, \@volume(\@issue), \@pagenumbers}}
\fancyfoot[CE]{\thepage}

% 首页特殊样式
\fancypagestyle{firstpage}{
  \fancyhf{}
  \renewcommand{\headrulewidth}{0pt}
  \fancyhead[L]{%
    \begin{minipage}[t]{0.55\textwidth}
      \raggedright
      {\small\bfseries\color[RGB]{31,73,125}\MakeUppercase{\@journalabbrevname}}\\[1pt]
      {\small Vol. \@volume, No. \@issue\ | pp. \@pagenumbers\ | \@publishedyear}
    \end{minipage}%
    \begin{minipage}[t]{0.45\textwidth}
      \raggedleft
      {\small\bfseries\color[RGB]{31,73,125}\@articletype}\\[1pt]
      {\small\color{black!60}\@doi}
    \end{minipage}%
    \par\vspace{4pt}%
    {\color[RGB]{31,73,125}\rule{\textwidth}{0.6pt}}%
  }
  \fancyfoot[C]{\thepage}
}

% ==============================================================================
% 10. 浮动体与特殊环境 (Floats & Special Environments)
% ==============================================================================
\RequirePackage{caption}
\captionsetup{labelsep=period, labelfont=bf}

% 宽版文本环境 (基于 cuted)
\newenvironment{widetext}{%
  \par\medskip
  \begin{strip}
    \centering \vspace{-10pt}
    \rule{0.9\textwidth}{0.4pt} \vspace{8pt}
    \setlength{\abovedisplayskip}{12pt}
    \setlength{\belowdisplayskip}{12pt}
    \par\interlinepenalty=10000
}{%
    \par\vspace{8pt}
    \rule{0.9\textwidth}{0.4pt} \vspace{4pt}
  \end{strip}
  \par\medskip
}

% 浮动体环境简化
\newenvironment{widefigure}[1][tbp]{\begin{figure*}[#1]}{\end{figure*}}
\newenvironment{widetable}[1][tbp]{\begin{table*}[#1]}{\end{table*}}

% 声明 Scheme 环境
\DeclareCaptionType[fileext=los]{scheme}[Scheme][List of Schemes]

% 文献规范
\RequirePackage[numbers,sort&compress]{natbib}
\setlength{\bibsep}{0pt plus 0.3ex}

% 期刊特定章节
\newenvironment{acknowledgments}{\section*{Acknowledgments}}{}
\newenvironment{Supporting_Information}{\section*{Supporting information}}{}
\newenvironment{Notes}{\section*{Notes}}{}

\endinput
